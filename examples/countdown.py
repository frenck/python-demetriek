import asyncio

from demetriek import LaMetricDevice, DeviceMode, Application


async def main() -> None:
    """Show how an app can be controlled from the API"""
    # Find the countdown app
    # Change mode to MANUAL
    # Set the duration to 5 seconds
    # Start the countdown
    # 8 seconds after starting the countdown, reset it again
    # Switch back to what-ever mode was selected before the script ran

    async with LaMetricDevice(
        "192.168.1.11",
        api_key="DEVICE_API_KEY",
    ) as lametric:
        # Find the countdown app
        apps = await lametric.apps()
        countdown: Application | None = apps.get("com.lametric.countdown")
        if not countdown:
            raise Exception("No countdown app")

        # we'll restore to the previous mode after we're done
        prev_mode = await lametric.mode()
        await lametric.mode(mode=DeviceMode.MANUAL)

        # find the widget
        if len(countdown.widgets) == 0:
            raise Exception("No countdown widget")
        widget_key = list(countdown.widgets.keys())[0]

        # we already know the parameters, but we just print them to show how
        # a client could get information about parameters
        print(countdown.actions["countdown.configure"])

        # configure countdown
        await lametric.do_action(package=countdown.package,
                                 action="countdown.configure",
                                 widget=widget_key,
                                 activate=True,
                                 params={
                                     "duration": 5,
                                 })

        # start countdown
        await lametric.do_action(package=countdown.package, action="countdown.start", widget=widget_key, activate=True)
        await asyncio.sleep(8)

        # the clock should be beeping now, reset it
        await lametric.do_action(package=countdown.package, action="countdown.reset", widget=widget_key, activate=True)

        # go back to the previous mode
        await lametric.mode(mode=prev_mode)


if __name__ == "__main__":
    asyncio.run(main())
