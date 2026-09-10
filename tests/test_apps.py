"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import aiohttp
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricDevice

from . import load_fixture


async def test_app_next(aresponses: ResponsesMockServer) -> None:
    """Test switching to the next app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/next",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps_next.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_next()


async def test_app_previous(aresponses: ResponsesMockServer) -> None:
    """Test switching to the previous app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/prev",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps_prev.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_previous()


async def test_apps(aresponses: ResponsesMockServer) -> None:
    """Test getting the installed apps."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        apps = await demetriek.apps()

    assert len(apps) == 6
    clock = apps["com.lametric.clock"]
    assert clock.package == "com.lametric.clock"
    assert clock.title == "Clock"
    assert clock.vendor == "LaMetric"
    assert clock.version == "2.8.10"
    assert clock.version_code == "44"

    # An action parameter constrained by a regular expression.
    alarm_time = clock.actions["clock.alarm"]["time"]
    assert alarm_time.data_type == "string"
    assert alarm_time.name == "time"
    assert alarm_time.required is False
    assert alarm_time.format == "[0-9]{2}:[0-9]{2}(?::[0-9]{2})?"

    # An action that takes no parameters.
    assert clock.actions["settings.dateFormats"] == {}

    # Trigger parameters carry no required flag.
    assert clock.triggers["alarm"]["snooze"].required is None

    widget = clock.widgets["1_com.lametric.clock"]
    assert widget.index == 0
    assert widget.package == "com.lametric.clock"
    assert widget.visible is True
    assert widget.settings == {"_title": "Clock"}

    # Apps with no actions leave the key out entirely.
    assert apps["com.lametric.custommessage"].actions == {}


async def test_app(aresponses: ResponsesMockServer) -> None:
    """Test getting a single installed app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        app = await demetriek.app(package="com.lametric.clock")

    assert app.package == "com.lametric.clock"
    assert app.title == "Clock"
    # This endpoint omits the widget visibility.
    assert app.widgets["1_com.lametric.clock"].visible is None


async def test_activate_widget(aresponses: ResponsesMockServer) -> None:
    """Test showing a specific widget."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/1_com.lametric.clock/activate",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app_action.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.activate_widget(
            package="com.lametric.clock",
            widget_id="1_com.lametric.clock",
        )


async def test_app_action(aresponses: ResponsesMockServer) -> None:
    """Test running an app action with parameters."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        assert await request.json() == {
            "id": "clock.alarm",
            "params": {"enabled": True, "time": "07:00:00"},
            "activate": True,
        }
        return aresponses.Response(
            status=201,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app_action.json"),
        )

    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/1_com.lametric.clock/actions",
        "POST",
        response_handler,
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_action(
            package="com.lametric.clock",
            widget_id="1_com.lametric.clock",
            action="clock.alarm",
            params={"enabled": True, "time": "07:00:00"},
            activate=True,
        )


async def test_app_action_without_params(aresponses: ResponsesMockServer) -> None:
    """Test running an app action that takes no parameters."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        assert await request.json() == {"id": "stopwatch.reset"}
        return aresponses.Response(
            status=201,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app_action.json"),
        )

    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.stopwatch"
        "/widgets/5_com.lametric.stopwatch/actions",
        "POST",
        response_handler,
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_action(
            package="com.lametric.stopwatch",
            widget_id="5_com.lametric.stopwatch",
            action="stopwatch.reset",
        )
