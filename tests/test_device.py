"""Asynchronous Python client for LaMetric TIME devices."""

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime

import pytest
from aioresponses import aioresponses
from syrupy.assertion import SnapshotAssertion
from yarl import URL

from demetriek import (
    AlarmSound,
    Chart,
    Device,
    DeviceMode,
    Goal,
    GoalData,
    LaMetricDevice,
    LaMetricError,
    Model,
    Notification,
    NotificationIconType,
    NotificationPriority,
    NotificationSound,
    NotificationSoundCategory,
    Simple,
    Sound,
    Update,
)
from demetriek.const import (
    NotificationType,
)

from .conftest import DEVICE_URL, load_fixture, request_json

# Real devices answer a dismissal with a success flag.
DISMISSED = '{"success": true}'


@pytest.mark.parametrize(
    "fixture",
    [
        "device.json",
        "device2.json",
        "device3.json",
        "device_sa5.json",
        "device_sa5_1.json",
        "device_lm37x8.json",
        "device_sa8.json",
    ],
)
async def test_get_device(
    responses: aioresponses,
    device: LaMetricDevice,
    fixture: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test getting device information."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device",
        status=200,
        body=load_fixture(fixture),
    )

    result = await device.device()

    assert asdict(result) == snapshot
    assert Device.from_dict(result.to_dict()) == result


async def test_get_device_unexpected_data(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test data the library does not understand raises a LaMetricError.

    So a firmware update that changes a response is reported with what did
    not fit, rather than with an error of the parsing library underneath.
    """
    responses.get(f"{DEVICE_URL}/api/v2/device", status=200, body='{"id": "1"}')

    with pytest.raises(
        LaMetricError, match=r"The LaMetric device at 127\.0\.0\.2"
    ) as error:
        await device.device()

    assert 'Field "display" of type Display is missing in Device' in str(error.value)


async def test_api_not_an_object(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test a response that is not an object at all raises a LaMetricError."""
    responses.get(f"{DEVICE_URL}/api/v2", status=200, body="[]")

    with pytest.raises(LaMetricError, match="should be a dict instance"):
        await device.api()


@pytest.mark.parametrize(
    ("call", "path", "body"),
    [
        ("display", "/api/v2/device/display", "{}"),
        ("audio", "/api/v2/device/audio", '{"volume": "loud"}'),
        ("bluetooth", "/api/v2/device/bluetooth", "{}"),
        ("wifi", "/api/v2/device/wifi", "{}"),
        ("apps", "/api/v2/device/apps", '{"com.lametric.clock": {}}'),
        ("stream", "/api/v2/device/stream", "{}"),
        ("notification_current", "/api/v2/device/notifications/current", '{"id": 1}'),
    ],
)
async def test_unexpected_data(
    responses: aioresponses,
    device: LaMetricDevice,
    call: str,
    path: str,
    body: str,
) -> None:
    """Test every endpoint raises a LaMetricError on data it does not understand."""
    responses.get(f"{DEVICE_URL}{path}", status=200, body=body)

    with pytest.raises(LaMetricError, match="data this library does not understand"):
        await getattr(device, call)()


async def test_get_device_wifi_not_an_object(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test a Wi-Fi block that is not an object raises a LaMetricError."""
    data = json.loads(load_fixture("device.json"))
    data["wifi"] = "unexpected"
    responses.get(f"{DEVICE_URL}/api/v2/device", status=200, body=json.dumps(data))

    with pytest.raises(LaMetricError, match='Field "wifi"'):
        await device.device()


async def test_get_device_wifi_connecting(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test a device still connecting to its Wi-Fi does not fail the update.

    A real TIME answered like this in home-assistant/core#97575. Only the
    Wi-Fi details are missing, the rest of the device is still there.
    """
    responses.get(
        f"{DEVICE_URL}/api/v2/device",
        status=200,
        body=load_fixture("device_wifi_connecting.json"),
    )

    result = await device.device()

    assert result.wifi.available is True
    assert result.wifi.rssi == 18
    assert result.wifi.active is None
    assert result.wifi.ip is None
    assert result.wifi.mac is None
    assert result.wifi.netmask is None
    assert result.wifi.ssid is None
    assert result.display.brightness is not None
    assert result.audio is not None


async def test_get_device_update(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test an available firmware update is exposed as an Update."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device",
        status=200,
        body=load_fixture("device_sa5_1.json"),
    )

    result = await device.device()

    assert isinstance(result.update, Update)
    assert result.update.version == "3.2.1"


async def test_notify(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test sending notification serialization."""
    url = f"{DEVICE_URL}/api/v2/device/notifications"
    responses.post(url, status=200, body=load_fixture("notification.json"))

    notification = Notification(
        icon_type=NotificationIconType.ALERT,
        notification_type=NotificationType.EXTERNAL,
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
    response = await device.notify(notification=notification)

    # check response
    assert response == 1
    # check on serialized request if aliases are used and null values are removed
    request = request_json(responses, "POST", url)
    assert request["type"] == "external"
    assert request["icon_type"] == "alert"
    assert "lifetime" not in request
    assert "unit" in request["model"]["frames"][1]["goalData"]
    assert "icon" not in request["model"]["frames"][2]
    assert request["model"]["sound"]["id"] == "win"
    assert request["model"]["sound"]["category"] == "notifications"
    assert request["model"]["frames"][0]["text"] == "Yeah"
    assert request["model"]["frames"][1]["goalData"]["current"] == 65
    assert request["model"]["frames"][2]["chartData"] == [1, 2, 3, 4, 5, 4, 3, 2, 1]


async def test_set_device_mode(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test setting the device mode."""
    url = f"{DEVICE_URL}/api/v2/device"
    responses.put(url, status=200, body=load_fixture("device_set_mode.json"))

    await device.set_device_mode(mode=DeviceMode.KIOSK)

    assert request_json(responses, "PUT", url) == {"mode": "kiosk"}


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("LM 37X8", "TIME"),
        ("sa8", "TIME"),
        ("sa5", "SKY"),
        ("something-new", None),
    ],
)
async def test_device_model_name(
    responses: aioresponses,
    device: LaMetricDevice,
    model: str,
    expected: str | None,
) -> None:
    """Test the reported model is translated to a product name."""
    payload = json.loads(load_fixture("device3.json"))
    payload["model"] = model
    responses.get(f"{DEVICE_URL}/api/v2/device", status=200, body=json.dumps(payload))

    info = await device.device()

    assert info.model_name == expected
    # The raw identifier stays available; consumers match on it.
    assert info.model == model


async def test_notification(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting a single notification."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/25",
        status=200,
        body=load_fixture("notification_get.json"),
    )

    notification = await device.notification(notification_id=25)

    # The device sends the ID as a string.
    assert notification.notification_id == 25
    assert notification.notification_type is NotificationType.EXTERNAL
    assert notification.priority is NotificationPriority.INFO
    assert notification.model.frames == [Simple(text="fixture")]


async def test_notification_queue(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test getting all notifications in the queue."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body=load_fixture("notification_queue.json"),
    )

    notifications = await device.notification_queue()

    assert [notification.notification_id for notification in notifications] == [
        25,
        26,
    ]
    assert notifications[0].priority is NotificationPriority.CRITICAL


async def test_notification_current(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test getting the notification currently on display."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body=load_fixture("notification_get.json"),
    )

    notification = await device.notification_current()

    assert notification
    assert notification.notification_id == 25


async def test_notification_current_none(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test getting the current notification when nothing is on display."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body="{}",
    )

    assert await device.notification_current() is None


async def test_dismiss_notification(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test dismissing a single notification."""
    url = f"{DEVICE_URL}/api/v2/device/notifications/25"
    responses.delete(url, status=200, body='{"success": true}')

    await device.dismiss_notification(notification_id=25)

    assert ("DELETE", URL(url)) in responses.requests


async def test_dismiss_all_notifications(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test all notifications are dismissed, last in the queue first."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body=load_fixture("notification_queue.json"),
    )
    responses.delete(f"{DEVICE_URL}/api/v2/device/notifications/25", body=DISMISSED)
    responses.delete(f"{DEVICE_URL}/api/v2/device/notifications/26", body=DISMISSED)

    await device.dismiss_all_notifications()

    dismissed = [url.path for method, url in responses.requests if method == "DELETE"]
    assert dismissed == [
        "/api/v2/device/notifications/26",
        "/api/v2/device/notifications/25",
    ]


async def test_dismiss_all_notifications_empty_queue(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test nothing is dismissed when the queue is empty."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body="[]",
    )

    await device.dismiss_all_notifications()

    assert all(method == "GET" for method, _ in responses.requests)


async def test_dismiss_current_notification(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test dismissing the notification currently on display."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body=load_fixture("notification_get.json"),
    )
    url = f"{DEVICE_URL}/api/v2/device/notifications/25"
    responses.delete(url, body=DISMISSED)

    await device.dismiss_current_notification()

    assert ("DELETE", URL(url)) in responses.requests


async def test_dismiss_current_notification_none(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test nothing is dismissed when no notification is on display."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body="{}",
    )

    await device.dismiss_current_notification()

    assert all(method == "GET" for method, _ in responses.requests)


async def test_dismiss_current_notification_unsupported(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the notification on display is dismissed, even if it does not parse."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body='{"id": "26", "model": {"frames": [{"icon": 1, "unknown": true}]}}',
    )
    url = f"{DEVICE_URL}/api/v2/device/notifications/26"
    responses.delete(url, body=DISMISSED)

    await device.dismiss_current_notification()

    assert ("DELETE", URL(url)) in responses.requests


@pytest.mark.parametrize(
    ("sound", "category"),
    [
        (AlarmSound.ALARM1, NotificationSoundCategory.ALARMS),
        (NotificationSound.WIN, NotificationSoundCategory.NOTIFICATIONS),
    ],
)
def test_sound_infers_category(
    sound: AlarmSound | NotificationSound,
    category: NotificationSoundCategory,
) -> None:
    """Test the sound category is inferred from the sound."""
    assert Sound(sound=sound).category is category


def test_sound_keeps_explicit_category() -> None:
    """Test an explicitly set sound category is not overridden."""
    sound = Sound(
        sound=NotificationSound.WIN,
        category=NotificationSoundCategory.ALARMS,
    )

    assert sound.category is NotificationSoundCategory.ALARMS


UNSUPPORTED_QUEUE = """[
  {"id": "25", "model": {"frames": [{"text": "first"}]}, "type": "external"},
  {"id": "26", "model": {"frames": [{"icon": 1, "unknown": true}]}, "type": "internal"}
]"""


async def test_notification_queue_skips_unsupported(
    responses: aioresponses,
    device: LaMetricDevice,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test one unsupported notification does not break the whole queue."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body=UNSUPPORTED_QUEUE,
    )

    with caplog.at_level(logging.WARNING):
        notifications = await device.notification_queue()

    assert [notification.notification_id for notification in notifications] == [25]
    assert "Skipping notification 26" in caplog.text


async def test_notification_queue_skips_null(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test an empty entry in the queue does not break the whole queue."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body='[null, {"id": "25", "model": {"frames": [{"text": "first"}]}}]',
    )

    notifications = await device.notification_queue()

    assert [notification.notification_id for notification in notifications] == [25]


async def test_dismiss_all_notifications_unsupported(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test notifications are dismissed, even the ones that do not parse."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body=UNSUPPORTED_QUEUE,
    )
    responses.delete(f"{DEVICE_URL}/api/v2/device/notifications/25", body=DISMISSED)
    responses.delete(f"{DEVICE_URL}/api/v2/device/notifications/26", body=DISMISSED)

    await device.dismiss_all_notifications()

    dismissed = [url.path for method, url in responses.requests if method == "DELETE"]
    assert dismissed == [
        "/api/v2/device/notifications/26",
        "/api/v2/device/notifications/25",
    ]


def test_misspelled_sound_names_are_aliases() -> None:
    """Test the old misspelled sound names still resolve to the right sound."""
    assert NotificationSound.NETGATIVE1 is NotificationSound.NEGATIVE1
    assert NotificationSound("negative1").name == "NEGATIVE1"


@pytest.mark.parametrize(
    ("fixture", "version", "streaming"),
    [
        # The TIME from before 2022 reports API 2.3.0, without streaming.
        ("api.json", "2.3.0", False),
        ("api_sa8.json", "2.4.0", True),
    ],
)
async def test_api(
    responses: aioresponses,
    device: LaMetricDevice,
    fixture: str,
    version: str,
    streaming: bool,  # noqa: FBT001
) -> None:
    """Test getting the API version and the available endpoints."""
    responses.get(f"{DEVICE_URL}/api/v2", status=200, body=load_fixture(fixture))

    api = await device.api()

    assert api.api_version == version
    assert api.api_version >= "2.1.0"
    assert api.endpoints["device_url"] == f"{DEVICE_URL}/api/v2/device"
    assert ("stream_url" in api.endpoints) is streaming


async def test_notification_updated(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the time a notification was last updated is parsed."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/25",
        status=200,
        body=load_fixture("notification_get.json"),
    )

    notification = await device.notification(notification_id=25)

    assert notification.updated == datetime(2026, 9, 10, 17, 50, 38, tzinfo=UTC)


async def test_notify_lifetime(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test the notification lifetime is sent under the key the device accepts."""
    url = f"{DEVICE_URL}/api/v2/device/notifications"
    responses.post(url, status=201, body=load_fixture("notification.json"))

    await device.notify(
        notification=Notification(
            life_time=5000,
            model=Model(frames=[Simple(text="Short lived")]),
        )
    )

    request = request_json(responses, "POST", url)
    assert request["lifetime"] == 5000
    assert "life_time" not in request
    assert "lifeTime" not in request


async def test_notify_frame_duration(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test frames send their duration, and leave it out when not set."""
    url = f"{DEVICE_URL}/api/v2/device/notifications"
    responses.post(url, status=201, body=load_fixture("notification.json"))

    await device.notify(
        notification=Notification(
            model=Model(
                frames=[
                    Simple(text="Short", duration=1000),
                    Goal(data=GoalData(current=1, end=2, start=0), duration=5000),
                    Chart(data=[1, 2, 3], duration=10000),
                    Chart(data=[3, 2, 1]),
                ]
            )
        )
    )

    frames = request_json(responses, "POST", url)["model"]["frames"]
    assert [frame.get("duration") for frame in frames] == [1000, 5000, 10000, None]
    assert "duration" not in frames[3]


async def test_notification_frame_duration(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the duration of frames in the queue is parsed."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/7",
        status=200,
        body=(
            '{"id": "7", "model": {"frames": ['
            '{"duration": 1000, "icon": 3219, "text": "N 1S"},'
            '{"duration": 10000, "icon": 7956, "text": "N 10S"}]}}'
        ),
    )

    notification = await device.notification(notification_id=7)

    assert notification.model.frames == [
        Simple(text="N 1S", icon=3219, duration=1000),
        Simple(text="N 10S", icon=7956, duration=10000),
    ]


@pytest.mark.parametrize("generation", ["lm37x8", "sa8"])
async def test_notification_queue_real(
    responses: aioresponses,
    device: LaMetricDevice,
    snapshot: SnapshotAssertion,
    generation: str,
) -> None:
    """Test a queue captured from a real device, with every frame type."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications",
        status=200,
        body=load_fixture(f"notification_queue_{generation}.json"),
    )

    notifications = await device.notification_queue()

    # The device orders the queue by priority, then by arrival.
    assert [notification.priority for notification in notifications] == [
        NotificationPriority.CRITICAL,
        NotificationPriority.WARNING,
        NotificationPriority.INFO,
        NotificationPriority.INFO,
    ]
    assert [type(frame) for frame in notifications[1].model.frames] == [Goal, Chart]

    # The device does not keep the icon type it was sent.
    assert all(notification.icon_type is None for notification in notifications)

    assert [asdict(notification) for notification in notifications] == snapshot


async def test_notification_current_real(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the notification on display, as captured from a real device."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/current",
        status=200,
        body=load_fixture("notification_current_sa8.json"),
    )

    notification = await device.notification_current()

    assert notification
    assert notification.notification_id == 5
    assert notification.priority is NotificationPriority.WARNING
    assert notification.model.cycles == 0
    assert notification.model.frames == [Simple(text="current?", icon=3219)]
