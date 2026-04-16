"""Goto a target and start stacking.

Usage:
    python goto_and_stack.py <device-ip>
"""

import asyncio
import logging
import sys

import seestar

logging.basicConfig(level=logging.INFO)

# M42 - Orion Nebula
TARGET_NAME = "M42"
TARGET_RA = 5.588   # hours
TARGET_DEC = -5.39  # degrees


async def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <device-ip>")
        return

    host = sys.argv[1]

    async with seestar.SeestarClient(host) as client:
        print(f"Connected. Going to {TARGET_NAME}...")

        # Set up event handler to track goto progress
        async def on_goto(event: seestar.EventMessage):
            print(f"  AutoGoto: {event.state}")

        client.events.on("AutoGoto", on_goto)

        # Start view and goto
        await client.view.start(
            mode="star",
            target_name=TARGET_NAME,
            target_ra_dec=[TARGET_RA / 15, TARGET_DEC],  # RA in hours/15
            lp_filter=False,
        )

        # Wait for goto to complete (monitor via events)
        await asyncio.sleep(30)

        # Start stacking
        print("\nStarting stacking...")
        await client.stack.start(restart=True)

        # Monitor for a while
        async def on_stack(event: seestar.EventMessage):
            print(f"  Stack: {event.state}")

        client.events.on("Stack", on_stack)

        # Let it stack for 5 minutes
        await asyncio.sleep(300)

        # Save the result
        print("\nSaving stacked image...")
        await client.camera.save_stack()

        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
