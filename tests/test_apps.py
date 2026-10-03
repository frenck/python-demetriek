"""Asynchronous Python client for LaMetric TIME devices."""

from aioresponses import aioresponses

from demetriek import Chart, Goal, GoalData, LaMetricDevice, Simple

from .conftest import DEVICE_URL, load_fixture, request_json


async def test_app_next(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test switching to the next app."""
    responses.put(
        f"{DEVICE_URL}/api/v2/device/apps/next",
        status=200,
        body=load_fixture("apps_next.json"),
    )

    await device.app_next()


async def test_app_previous(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test switching to the previous app."""
    responses.put(
        f"{DEVICE_URL}/api/v2/device/apps/prev",
        status=200,
        body=load_fixture("apps_prev.json"),
    )

    await device.app_previous()


async def test_apps(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting the installed apps."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/apps",
        status=200,
        body=load_fixture("apps.json"),
    )

    apps = await device.apps()

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


async def test_app(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting a single installed app."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/apps/com.lametric.clock",
        status=200,
        body=load_fixture("app.json"),
    )

    app = await device.app(package="com.lametric.clock")

    assert app.package == "com.lametric.clock"
    assert app.title == "Clock"
    # This endpoint omits the widget visibility.
    assert app.widgets["1_com.lametric.clock"].visible is None


async def test_activate_widget(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test showing a specific widget."""
    responses.put(
        f"{DEVICE_URL}/api/v2/device/apps/com.lametric.clock"
        "/widgets/1_com.lametric.clock/activate",
        status=200,
        body=load_fixture("app_action.json"),
    )

    await device.activate_widget(
        package="com.lametric.clock",
        widget_id="1_com.lametric.clock",
    )


async def test_app_action(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test running an app action with parameters."""
    url = (
        f"{DEVICE_URL}/api/v2/device/apps/com.lametric.clock"
        "/widgets/1_com.lametric.clock/actions"
    )
    responses.post(url, status=201, body=load_fixture("app_action.json"))

    await device.app_action(
        package="com.lametric.clock",
        widget_id="1_com.lametric.clock",
        action="clock.alarm",
        params={"enabled": True, "time": "07:00:00"},
        activate=True,
    )

    assert request_json(responses, "POST", url) == {
        "id": "clock.alarm",
        "params": {"enabled": True, "time": "07:00:00"},
        "activate": True,
    }


async def test_app_action_without_params(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test running an app action that takes no parameters."""
    url = (
        f"{DEVICE_URL}/api/v2/device/apps/com.lametric.stopwatch"
        "/widgets/5_com.lametric.stopwatch/actions"
    )
    responses.post(url, status=201, body=load_fixture("app_action.json"))

    data = await device.app_action(
        package="com.lametric.stopwatch",
        widget_id="5_com.lametric.stopwatch",
        action="stopwatch.reset",
    )

    assert request_json(responses, "POST", url) == {"id": "stopwatch.reset"}
    assert data == {}


async def test_app_action_returns_data(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the data an app returns for an action is passed on.

    The payload is made up: a real radio that is not playing answers
    `radio.state` with empty data, which would not show the data is passed on.
    """
    url = (
        f"{DEVICE_URL}/api/v2/device/apps/com.lametric.radio"
        "/widgets/3_com.lametric.radio/actions"
    )
    responses.post(url, status=201, body=load_fixture("app_action_data.json"))

    data = await device.app_action(
        package="com.lametric.radio",
        widget_id="3_com.lametric.radio",
        action="radio.state",
    )

    assert data == {"state": "playing"}


async def test_update_widget(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test pushing frames to a widget, such as one of the My Data DIY app."""
    url = (
        f"{DEVICE_URL}/api/v2/widget/update/com.lametric.diy.devwidget"
        "/db406c69bd5c4fec9a476eccef9683d6"
    )
    # The device answers a successful update with an empty JSON response.
    responses.post(url, status=200, body="")

    await device.update_widget(
        package="com.lametric.diy.devwidget",
        widget_id="db406c69bd5c4fec9a476eccef9683d6",
        frames=[
            Simple(text="21.5°C", icon=3219),
            Goal(icon=7956, data=GoalData(start=0, current=42, end=100, unit="%")),
            Chart(data=[1, 3, 5, 7, 5, 3, 1]),
        ],
    )

    assert request_json(responses, "POST", url) == {
        "frames": [
            {"text": "21.5°C", "icon": 3219},
            {
                "goalData": {"start": 0, "current": 42, "end": 100, "unit": "%"},
                "icon": 7956,
            },
            {"chartData": [1, 3, 5, 7, 5, 3, 1]},
        ]
    }
