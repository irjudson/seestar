"""Discover Seestar devices and connect to the first one found.

Usage:
    python discover_and_connect.py              # auto-discover via UDP
    python discover_and_connect.py <device-ip>  # connect directly by IP
"""

import asyncio
import logging
import sys

import seestar

logging.basicConfig(level=logging.INFO)


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else None

    if host is None:
        # Discover devices on the network
        print("Scanning for Seestar devices...")
        devices = await seestar.discover(timeout=5.0)

        if not devices:
            print("No devices found. Try passing the IP directly:")
            print(f"  python {sys.argv[0]} <device-ip>")
            return

        for dev in devices:
            print(f"  Found: {dev.info.product_model} at {dev.host} (SN: {dev.info.sn})")

        host = devices[0].host
    else:
        print(f"Using provided address: {host}")

    print(f"\nConnecting to {host}...")

    async with seestar.SeestarClient(host) as client:
        # Get device state
        state = await client.get_device_state()
        print(f"\nDevice: {state.device.name if state.device else 'Unknown'}")
        print(f"Firmware: {state.device.firmware_ver_string if state.device else '?'}")
        print(f"Serial: {state.device.sn if state.device else '?'}")

        if state.pi_status:
            print(f"Temperature: {state.pi_status.temp}°C")
            print(f"Battery: {state.pi_status.battery_capacity}%")

        if state.mount:
            print(f"Tracking: {state.mount.tracking}")
            print(f"EQ Mode: {state.mount.equ_mode}")

        # Get current coordinates
        coord = await client.mount.get_equ_coord()
        print(f"\nRA: {coord.ra:.4f}h  Dec: {coord.dec:.4f}°")


if __name__ == "__main__":
    asyncio.run(main())
