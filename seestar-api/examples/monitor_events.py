"""Connect and monitor all events from the device.

Usage:
    python monitor_events.py <device-ip>
"""

import asyncio
import logging
import sys

import seestar

logging.basicConfig(level=logging.INFO)


async def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <device-ip>")
        return

    host = sys.argv[1]

    async with seestar.SeestarClient(host) as client:
        print("Connected. Monitoring events (Ctrl+C to stop)...\n")

        def on_event(event: seestar.EventMessage):
            extra = {k: v for k, v in event.model_dump().items() if k not in ("Event", "state")}
            extra_str = f"  {extra}" if extra else ""
            print(f"[{event.Event}] state={event.state}{extra_str}")

        client.events.on_all(on_event)

        # Keep connection alive indefinitely
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
