# pylint: disable=W0621
"""Asynchronous Python client for LaMetric TIME devices."""

import asyncio

from demetriek import (
    Chart,
    Goal,
    GoalData,
    LaMetricDevice,
    Model,
    Notification,
    NotificationIconType,
    NotificationSound,
    Simple,
    Sound,
)


async def main() -> None:
    """Show example on controlling your LaMetric device."""
    # Create a alert notification, with 3 message frames.
    # First frame is a text, the second is a goal, last one
    # shows a chart. Additionally, the WIN notification sound
    # is played.
    notification = Notification(
        icon_type=NotificationIconType.ALERT,
        model=Model(
            frames=[
                Simple(text="Yeah", icon=18815),
                Goal(
                    icon=7956,
                    data=GoalData(
                        current=65,
                        end=100,
                        start=0,
                        unit="%",
                    ),
                ),
                Chart(data=[1, 2, 3, 4, 5, 4, 3, 2, 1]),
            ],
            sound=Sound(sound=NotificationSound.WIN),
        ),
    )

    async with LaMetricDevice(
        "192.168.1.11",
        api_key="DEVICE_API_KEY",
    ) as lametric:
        # Raise audio volume... to we can hear the notification
        await lametric.audio(volume=100)

        # Send notification
        await lametric.notify(notification=notification)


if __name__ == "__main__":
    asyncio.run(main())
