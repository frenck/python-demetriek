"""Asynchronous Python client for LaMetric TIME devices."""

import asyncio

from demetriek import LaMetricDevice, LaMetricStream

HOST = "192.168.1.11"


async def main() -> None:
    """Show a green bar sweeping across the screen of your LaMetric device."""
    async with LaMetricDevice(HOST, api_key="DEVICE_API_KEY") as lametric:
        # Not every device can stream, for example an LM 37X8 TIME on
        # firmware 2.x. The device lists the stream endpoints when it can.
        api = await lametric.api()
        if "stream_url" not in api.endpoints:
            print("This device does not support streaming")
            return

        # The canvas size differs per device, so ask the device for it.
        status = await lametric.stream()
        if status.canvas.pixel is None:
            print("This device has no pixel canvas to stream to")
            return
        width = status.canvas.pixel.size.width
        height = status.canvas.pixel.size.height

        session = await lametric.stream_start()
        try:
            async with LaMetricStream(host=HOST, session=session) as stream:
                # About four seconds at 30 frames per second.
                for step in range(120):
                    column = step % width

                    # Raw frames are RGB888, three bytes for every pixel.
                    frame = bytearray(width * height * 3)
                    for row in range(height):
                        green = (row * width + column) * 3 + 1
                        frame[green] = 255

                    stream.send(bytes(frame), width=width, height=height)
                    await asyncio.sleep(1 / 30)
        finally:
            # Always give the screen back to the device.
            await lametric.stream_stop()


if __name__ == "__main__":
    asyncio.run(main())
