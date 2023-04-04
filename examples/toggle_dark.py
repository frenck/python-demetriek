import asyncio
from demetriek import LaMetricDevice, DeviceMode, Application


async def main() -> None:
    """Show how to manually select which app is visible."""
    # Imagine this script is triggered by a smart home,
    # and when it's bedtime the script will switch
    # the LaMetric clock to manual mode and activate the "Dark" app
    # (na app which just blanks the screen)
    async with LaMetricDevice(
        "192.168.1.11",
        api_key="DEVICE_API_KEY",
    ) as lametric:
        # Find the "Dark" app: https://apps.lametric.com/apps/dark/542
        apps = await lametric.apps()
        dark_app: Application | None = None
        for app in apps.values():
            if app.title == "Dark":
                dark_app = app

        if not dark_app:
            raise Exception("Dark app not found")

        # activate dark
        package = dark_app.package
        if len(dark_app.widgets) == 0:
            raise Exception("Dark app has no widgets")
        widget = list(dark_app.widgets.keys())[0]  # dark only have one widget

        # toggle between AUTO and MANUAL
        mode = await lametric.mode()
        if mode == DeviceMode.AUTO:
            # Switch to manual
            await lametric.mode(mode=DeviceMode.MANUAL)
            await lametric.activate_widget(package=package, widget=widget)
        else:
            # back to auto
            await lametric.mode(mode=DeviceMode.AUTO)


if __name__ == "__main__":
    asyncio.run(main())
