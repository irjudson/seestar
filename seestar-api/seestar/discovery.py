"""UDP device discovery for Seestar telescopes.

Broadcasts scan_iscope on port 4720 and parses responses to find
Seestar devices on the local network.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import socket
import struct
from typing import AsyncIterator

from .constants import COMMAND_PORT, DISCOVERY_PORT
from .models import DiscoveredDevice, DiscoveryResult

logger = logging.getLogger(__name__)

_SCAN_METHOD = "scan_iscope"


def _get_broadcast_addresses() -> list[str]:
    """Get broadcast addresses for all active network interfaces."""
    addrs = []
    try:
        import netifaces
        for iface in netifaces.interfaces():
            af_inet = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
            for info in af_inet:
                bcast = info.get("broadcast")
                if bcast and bcast != "127.255.255.255":
                    addrs.append(bcast)
    except ImportError:
        # Fallback: try to get broadcast from ioctl on Linux
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for iface_name in _get_interface_names():
                try:
                    bcast = socket.inet_ntoa(
                        fcntl.ioctl(
                            sock.fileno(),
                            0x8919,  # SIOCGIFBRDADDR
                            struct.pack("256s", iface_name.encode("utf-8")[:15]),
                        )[20:24]
                    )
                    if bcast != "0.0.0.0":
                        addrs.append(bcast)
                except OSError:
                    pass
            sock.close()
        except Exception:
            pass

    if not addrs:
        addrs.append("255.255.255.255")
    return addrs


def _get_interface_names() -> list[str]:
    """Get network interface names from /proc/net/dev."""
    names = []
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" in line:
                    name = line.split(":")[0].strip()
                    if name != "lo":
                        names.append(name)
    except FileNotFoundError:
        pass
    return names


def _make_scan_message(seq: int) -> bytes:
    msg = json.dumps({"method": _SCAN_METHOD, "params": "", "id": seq})
    return (msg + "\r\n").encode("utf-8")


def _parse_response(data: bytes, addr: tuple[str, int]) -> DiscoveredDevice | None:
    try:
        payload = json.loads(data.decode("utf-8").strip())
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.debug("Invalid discovery response from %s", addr)
        return None

    if payload.get("method") != _SCAN_METHOD:
        return None

    result = payload.get("result", {})
    try:
        info = DiscoveryResult.model_validate(result)
    except Exception:
        logger.debug("Failed to parse discovery result from %s: %s", addr, result)
        return None

    return DiscoveredDevice(host=addr[0], port=COMMAND_PORT, info=info)


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for device discovery."""

    def __init__(self, found: asyncio.Queue[DiscoveredDevice]) -> None:
        self._found = found
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        device = _parse_response(data, addr)
        if device is not None:
            self._found.put_nowait(device)

    def error_received(self, exc: Exception) -> None:
        logger.debug("Discovery UDP error: %s", exc)


async def discover(
    timeout: float = 5.0,
    broadcast_addr: str | None = None,
    interval: float = 1.0,
) -> list[DiscoveredDevice]:
    """Discover Seestar devices on the local network.

    Args:
        timeout: Total time to listen for responses (seconds).
        broadcast_addr: UDP broadcast address. If None, broadcasts on all
            detected subnet broadcast addresses automatically.
        interval: Time between broadcast packets (seconds).

    Returns:
        List of discovered devices (deduplicated by serial number).
    """
    if broadcast_addr is not None:
        addrs = [broadcast_addr]
    else:
        addrs = _get_broadcast_addresses()
    logger.debug("Discovery broadcast addresses: %s", addrs)

    found: asyncio.Queue[DiscoveredDevice] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    # Create UDP broadcast socket
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: _DiscoveryProtocol(found),
        local_addr=("0.0.0.0", 0),
        family=socket.AF_INET,
        allow_broadcast=True,
    )

    try:
        sock = transport.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        seq = 1
        deadline = loop.time() + timeout
        seen: dict[str, DiscoveredDevice] = {}

        while loop.time() < deadline:
            # Send broadcast on all addresses
            msg = _make_scan_message(seq)
            for addr in addrs:
                transport.sendto(msg, (addr, DISCOVERY_PORT))
            seq += 1

            # Collect responses for one interval
            try:
                async with asyncio.timeout(min(interval, deadline - loop.time())):
                    while True:
                        device = await found.get()
                        if device.info.sn and device.info.sn not in seen:
                            logger.info("Discovered %s at %s (SN: %s)", device.info.product_model, device.host, device.info.sn)
                            seen[device.info.sn] = device
            except (TimeoutError, asyncio.TimeoutError):
                pass

        return list(seen.values())
    finally:
        transport.close()


async def discover_iter(
    timeout: float = 30.0,
    broadcast_addr: str | None = None,
    interval: float = 1.0,
) -> AsyncIterator[DiscoveredDevice]:
    """Yield Seestar devices as they are discovered.

    Args:
        timeout: Total time to listen (seconds).
        broadcast_addr: UDP broadcast address. If None, broadcasts on all
            detected subnet broadcast addresses automatically.
        interval: Time between broadcast packets (seconds).

    Yields:
        Newly discovered devices (deduplicated by serial number).
    """
    if broadcast_addr is not None:
        addrs = [broadcast_addr]
    else:
        addrs = _get_broadcast_addresses()

    found: asyncio.Queue[DiscoveredDevice] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: _DiscoveryProtocol(found),
        local_addr=("0.0.0.0", 0),
        family=socket.AF_INET,
        allow_broadcast=True,
    )

    try:
        sock = transport.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        seq = 1
        deadline = loop.time() + timeout
        seen: set[str] = set()

        while loop.time() < deadline:
            msg = _make_scan_message(seq)
            for addr in addrs:
                transport.sendto(msg, (addr, DISCOVERY_PORT))
            seq += 1

            try:
                async with asyncio.timeout(min(interval, deadline - loop.time())):
                    while True:
                        device = await found.get()
                        if device.info.sn and device.info.sn not in seen:
                            seen.add(device.info.sn)
                            yield device
            except (TimeoutError, asyncio.TimeoutError):
                pass
    finally:
        transport.close()
