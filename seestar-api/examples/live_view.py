"""Connect to the image stream and read frames.

Usage:
    python live_view.py <device-ip>
"""

import asyncio
import logging
import sys

from seestar.imaging import ImageStream

logging.basicConfig(level=logging.INFO)


async def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <device-ip>")
        return

    host = sys.argv[1]

    # Connect to telephoto image stream
    stream = ImageStream.telephoto(host)
    await stream.connect()
    print("Connected to image stream.")

    # Start streaming
    await stream.start_streaming()
    print("Streaming started. Reading frames...\n")

    frame_count = 0
    async for msg in stream.frames():
        if isinstance(msg, dict):
            print(f"  Control: {msg}")
        else:
            frame_count += 1
            print(f"  Frame {frame_count}: {len(msg)} bytes")

        if frame_count >= 10:
            break

    await stream.stop_streaming()
    await stream.close()
    print(f"\nReceived {frame_count} frames.")


if __name__ == "__main__":
    asyncio.run(main())
