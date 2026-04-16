"""Image stream reader for Seestar live view.

Connects to ports 4800 (telephoto) or 4804 (wide-angle) to receive
live preview images. Uses the same line-delimited JSON + heartbeat
protocol as the command socket.

Note: The exact binary frame format on these ports needs device
packet capture to fully confirm. This module provides the connection
and heartbeat scaffolding.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from .constants import HEARTBEAT_INTERVAL, HEARTBEAT_METHOD, IMAGE_PORT, IMAGE_WIDE_PORT

logger = logging.getLogger(__name__)

_TERMINATOR = b"\r\n"


class ImageStream:
    """Async reader for live image data from the Seestar.

    Usage::

        stream = ImageStream("<device-ip>")
        await stream.connect()

        async for frame in stream.frames():
            # frame is raw image bytes (JPEG or similar)
            process(frame)

        await stream.close()
    """

    def __init__(
        self,
        host: str,
        port: int = IMAGE_PORT,
        timeout: float = 10.0,
        heartbeat_interval: float = HEARTBEAT_INTERVAL,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._heartbeat_task: asyncio.Task | None = None

    @classmethod
    def telephoto(cls, host: str, **kwargs: object) -> ImageStream:
        """Create a stream for the telephoto camera (port 4800)."""
        return cls(host, port=IMAGE_PORT, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def wide(cls, host: str, **kwargs: object) -> ImageStream:
        """Create a stream for the wide-angle camera (port 4804)."""
        return cls(host, port=IMAGE_WIDE_PORT, **kwargs)  # type: ignore[arg-type]

    async def connect(self) -> None:
        """Connect to the image stream port."""
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Connected to image stream at %s:%d", self.host, self.port)

    async def close(self) -> None:
        """Close the image stream."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep stream alive."""
        msg = json.dumps({"method": HEARTBEAT_METHOD, "id": 1}) + "\r\n"
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                if self._writer is None:
                    break
                self._writer.write(msg.encode("utf-8"))
                await self._writer.drain()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.debug("Image stream heartbeat failed")

    async def send_command(self, method: str, params: dict | None = None) -> None:
        """Send a command on the image stream socket."""
        if self._writer is None:
            raise ConnectionError("Image stream not connected")
        cmd = {"method": method, "id": 1}
        if params:
            cmd["params"] = params
        line = json.dumps(cmd) + "\r\n"
        self._writer.write(line.encode("utf-8"))
        await self._writer.drain()

    async def start_streaming(self) -> None:
        """Send begin_streaming command."""
        await self.send_command("begin_streaming")

    async def stop_streaming(self) -> None:
        """Send stop_streaming command."""
        await self.send_command("stop_streaming")

    async def read_message(self) -> dict | bytes:
        """Read one message from the stream.

        Returns either a parsed JSON dict (for control messages)
        or raw bytes (for image data).
        """
        if self._reader is None:
            raise ConnectionError("Image stream not connected")

        line = await self._reader.readuntil(_TERMINATOR)
        text = line.decode("utf-8", errors="replace").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Might be binary image data with a header
            return line

    async def frames(self) -> AsyncIterator[dict | bytes]:
        """Yield frames from the image stream.

        Yields JSON dicts for control messages and raw bytes for image data.
        Filter for the type you need.
        """
        while True:
            try:
                msg = await self.read_message()
                yield msg
            except asyncio.IncompleteReadError:
                logger.debug("Image stream closed")
                break
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Image stream read error")
                break
