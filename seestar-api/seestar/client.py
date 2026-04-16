"""Core async TCP client for Seestar telescopes.

Handles connection, RSA handshake, heartbeat, command/response matching,
and event dispatch over line-delimited JSON on port 4700.
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import StrEnum
from typing import Any

from .commands import (
    CameraCommands,
    FocuserCommands,
    ImageCommands,
    MountCommands,
    PlanCommands,
    PolarAlignCommands,
    SensorCommands,
    SolveCommands,
    StackCommands,
    StreamCommands,
    SystemCommands,
    ViewCommands,
    WheelCommands,
)
from .constants import COMMAND_PORT, HEARTBEAT_INTERVAL, HEARTBEAT_METHOD, Cmd
from .crypto import load_private_key, sign_challenge
from .events import EventRouter
from .models import CommandRequest, CommandResponse, DeviceState

logger = logging.getLogger(__name__)

_TERMINATOR = b"\r\n"
_MAX_LINE = 1024 * 1024  # 1 MB max message size


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HANDSHAKE = "handshake"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class SeestarClient:
    """Async TCP client for controlling a Seestar telescope.

    Usage::

        client = SeestarClient("<device-ip>")
        await client.connect()

        state = await client.get_device_state()
        coord = await client.send_command("scope_get_equ_coord")

        await client.disconnect()

    Or as a context manager::

        async with SeestarClient("<device-ip>") as client:
            state = await client.get_device_state()
    """

    def __init__(
        self,
        host: str,
        port: int = COMMAND_PORT,
        timeout: float = 10.0,
        heartbeat_interval: float = HEARTBEAT_INTERVAL,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 3,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts

        self.events = EventRouter()
        self.state = ConnectionState.DISCONNECTED
        self.device_state: DeviceState | None = None

        # Command subsystems
        self.mount = MountCommands(self)
        self.camera = CameraCommands(self)
        self.focuser = FocuserCommands(self)
        self.wheel = WheelCommands(self)
        self.view = ViewCommands(self)
        self.stack = StackCommands(self)
        self.solve = SolveCommands(self)
        self.image = ImageCommands(self)
        self.stream = StreamCommands(self)
        self.polar_align = PolarAlignCommands(self)
        self.system = SystemCommands(self)
        self.plan = PlanCommands(self)
        self.sensor = SensorCommands(self)

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._tx_id = 1
        self._pending: dict[int, asyncio.Future[CommandResponse]] = {}
        self._heartbeat_task: asyncio.Task | None = None
        self._reader_task: asyncio.Task | None = None
        self._reconnect_count = 0
        self._priv_key = load_private_key()

    async def __aenter__(self) -> SeestarClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()

    # ── Connection lifecycle ───────────────────────────────────────

    async def connect(self) -> None:
        """Connect to the device and perform the RSA handshake."""
        if self.state == ConnectionState.CONNECTED:
            return

        self.state = ConnectionState.CONNECTING
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            self.state = ConnectionState.FAILED
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {exc}") from exc

        # Start background reader before handshake
        self._reader_task = asyncio.create_task(self._read_loop(), name="seestar-reader")

        # Perform RSA handshake
        self.state = ConnectionState.HANDSHAKE
        try:
            await self._handshake()
        except Exception:
            await self.disconnect()
            raise

        self.state = ConnectionState.CONNECTED
        self._reconnect_count = 0

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="seestar-heartbeat")

        logger.info("Connected to Seestar at %s:%d", self.host, self.port)

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        self.state = ConnectionState.DISCONNECTED

        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None

        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

        # Cancel all pending requests
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    @property
    def connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    # ── Handshake ──────────────────────────────────────────────────

    async def _handshake(self) -> None:
        """Perform the 2-step RSA handshake (get_verify_str + verify_client)."""
        # Step 1: Get challenge string
        resp = await self.send_command(Cmd.GET_VERIFY_STR)
        if resp.code != 0 or not isinstance(resp.result, dict):
            raise ConnectionError(f"get_verify_str failed: code={resp.code}")

        challenge = resp.result.get("str", "")
        if not challenge:
            raise ConnectionError("Empty challenge string from device")

        # Step 2: Sign challenge with SHA-1 + RSA and verify
        sign = sign_challenge(challenge, self._priv_key)
        resp = await self.send_command(
            Cmd.VERIFY_CLIENT,
            params={"sign": sign, "data": challenge},
        )

        if resp.code != 0:
            raise ConnectionError(f"verify_client failed: code={resp.code}")

        logger.debug("Handshake completed successfully")

    # ── Command sending ────────────────────────────────────────────

    def _next_id(self) -> int:
        tx_id = self._tx_id
        self._tx_id = (self._tx_id + 1) % (2**31)
        return tx_id

    async def send_command(
        self,
        method: str,
        params: dict[str, Any] | list[Any] | None = None,
        timeout: float | None = None,
    ) -> CommandResponse:
        """Send a command and wait for its response.

        Args:
            method: Command method string (e.g. "scope_get_equ_coord").
            params: Optional parameters dict or list.
            timeout: Response timeout in seconds (defaults to self.timeout).

        Returns:
            The parsed CommandResponse.

        Raises:
            ConnectionError: If not connected.
            asyncio.TimeoutError: If no response within timeout.
        """
        if self._writer is None:
            raise ConnectionError("Not connected")

        tx_id = self._next_id()
        request = CommandRequest(id=tx_id, method=method, params=params)

        # Register pending future
        fut: asyncio.Future[CommandResponse] = asyncio.get_running_loop().create_future()
        self._pending[tx_id] = fut

        # Send
        data = request.model_dump(exclude_none=True)
        line = json.dumps(data, separators=(",", ":")) + "\r\n"
        logger.debug("TX: %s", line.strip())
        try:
            self._writer.write(line.encode("utf-8"))
            await self._writer.drain()
        except Exception as exc:
            self._pending.pop(tx_id, None)
            raise ConnectionError(f"Send failed: {exc}") from exc

        # Wait for response
        try:
            return await asyncio.wait_for(fut, timeout=timeout or self.timeout)
        except asyncio.TimeoutError:
            self._pending.pop(tx_id, None)
            raise

    async def send_command_no_response(
        self,
        method: str,
        params: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        """Send a command without waiting for a response (fire-and-forget)."""
        if self._writer is None:
            raise ConnectionError("Not connected")

        tx_id = self._next_id()
        request = CommandRequest(id=tx_id, method=method, params=params)
        data = request.model_dump(exclude_none=True)
        line = json.dumps(data, separators=(",", ":")) + "\r\n"
        logger.debug("TX (no-wait): %s", line.strip())
        self._writer.write(line.encode("utf-8"))
        await self._writer.drain()

    # ── Background reader ──────────────────────────────────────────

    async def _read_loop(self) -> None:
        """Read lines from the socket and dispatch responses/events."""
        assert self._reader is not None
        try:
            while True:
                line = await self._reader.readuntil(_TERMINATOR)
                if not line:
                    break
                text = line.decode("utf-8").strip()
                if not text:
                    continue
                logger.debug("RX: %s", text[:500])
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON: %s", text[:200])
                    continue

                self._dispatch_message(data)

        except asyncio.IncompleteReadError:
            logger.debug("Connection closed by device")
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Reader loop error")

        # Connection lost
        if self.state == ConnectionState.CONNECTED:
            logger.warning("Connection lost to %s", self.host)
            await self._handle_disconnect()

    def _dispatch_message(self, data: dict[str, Any]) -> None:
        """Route an incoming message as either a command response or an event."""
        # Check if it's an event
        if "Event" in data:
            self.events.parse_and_dispatch(data)
            return

        # Check if it's a response to a pending command
        msg_id = data.get("id")
        if msg_id is not None and msg_id in self._pending:
            fut = self._pending.pop(msg_id)
            if not fut.done():
                try:
                    resp = CommandResponse.model_validate(data)
                    fut.set_result(resp)
                except Exception as exc:
                    fut.set_exception(exc)
            return

        # Heartbeat responses or unsolicited messages
        method = data.get("method", "")
        if method == HEARTBEAT_METHOD:
            return  # Heartbeat ACK, no action needed

        logger.debug("Unmatched message: %s", str(data)[:200])

    # ── Heartbeat ──────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        heartbeat_msg = json.dumps({"method": HEARTBEAT_METHOD, "id": 1}) + "\r\n"
        try:
            while self.state == ConnectionState.CONNECTED:
                await asyncio.sleep(self.heartbeat_interval)
                if self._writer is None:
                    break
                try:
                    self._writer.write(heartbeat_msg.encode("utf-8"))
                    await self._writer.drain()
                except Exception:
                    logger.debug("Heartbeat send failed")
                    break
        except asyncio.CancelledError:
            return

    # ── Reconnection ───────────────────────────────────────────────

    async def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection with optional reconnect."""
        old_state = self.state
        await self.disconnect()

        if not self.auto_reconnect or old_state != ConnectionState.CONNECTED:
            self.state = ConnectionState.FAILED
            return

        self.state = ConnectionState.RECONNECTING
        while self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            logger.info(
                "Reconnect attempt %d/%d to %s",
                self._reconnect_count,
                self.max_reconnect_attempts,
                self.host,
            )
            await asyncio.sleep(3.0)
            try:
                await self.connect()
                return
            except Exception:
                logger.debug("Reconnect attempt failed")

        self.state = ConnectionState.FAILED
        logger.error("Failed to reconnect after %d attempts", self.max_reconnect_attempts)

    # ── Convenience commands ───────────────────────────────────────

    async def get_device_state(self) -> DeviceState:
        """Get the complete device state."""
        resp = await self.send_command(Cmd.GET_DEVICE_STATE)
        if resp.code != 0:
            raise RuntimeError(f"get_device_state failed: code={resp.code}")
        state = DeviceState.model_validate(resp.result or {})
        self.device_state = state
        return state

    async def get_app_state(self) -> CommandResponse:
        """Get the current application state."""
        return await self.send_command(Cmd.GET_APP_STATE)

    async def shutdown(self) -> CommandResponse:
        """Shut down the device."""
        return await self.send_command(Cmd.PI_SHUTDOWN)

    async def reboot(self) -> CommandResponse:
        """Reboot the device."""
        return await self.send_command(Cmd.PI_REBOOT)
