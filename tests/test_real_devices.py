"""Asynchronous Python client for LaMetric TIME devices.

These fixtures are responses captured from real devices, one per hardware
generation: an LM 37X8 TIME from before 2022 on firmware 2.3.9, and an sa8
TIME on firmware 3.2.6. Only the values that identify the device or its
network are replaced.
"""

from dataclasses import asdict

import pytest
from aioresponses import aioresponses
from syrupy.assertion import SnapshotAssertion

from demetriek import LaMetricDevice, LaMetricError

from .conftest import DEVICE_URL, load_fixture

GENERATIONS = ["lm37x8", "sa8"]


def _path(method: str) -> str:
    """Return the endpoint a client method talks to."""
    return "/api/v2/device" if method == "device" else f"/api/v2/device/{method}"


@pytest.mark.parametrize("generation", GENERATIONS)
@pytest.mark.parametrize("method", ["device", "display", "audio", "bluetooth", "wifi"])
async def test_read(
    responses: aioresponses,
    device: LaMetricDevice,
    snapshot: SnapshotAssertion,
    generation: str,
    method: str,
) -> None:
    """Test every endpoint parses what each generation really sends."""
    responses.get(
        f"{DEVICE_URL}{_path(method)}",
        status=200,
        body=load_fixture(f"{method}_{generation}.json"),
    )

    result = await getattr(device, method)()

    assert asdict(result) == snapshot


@pytest.mark.parametrize("generation", GENERATIONS)
async def test_apps(
    responses: aioresponses,
    device: LaMetricDevice,
    snapshot: SnapshotAssertion,
    generation: str,
) -> None:
    """Test the installed apps of each generation parse."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/apps",
        status=200,
        body=load_fixture(f"apps_{generation}.json"),
    )

    apps = await device.apps()

    assert {package: asdict(app) for package, app in apps.items()} == snapshot


@pytest.mark.parametrize("generation", GENERATIONS)
@pytest.mark.parametrize(
    "change",
    [
        ("display", {"brightness": 100}),
        ("audio", {"volume": 50}),
        ("bluetooth", {"active": False}),
    ],
    ids=["display", "audio", "bluetooth"],
)
async def test_write(
    responses: aioresponses,
    device: LaMetricDevice,
    snapshot: SnapshotAssertion,
    generation: str,
    change: tuple[str, dict[str, object]],
) -> None:
    """Test the reply to a change is parsed for each generation."""
    method, kwargs = change
    responses.put(
        f"{DEVICE_URL}{_path(method)}",
        status=200,
        body=load_fixture(f"{method}_set_{generation}.json"),
    )

    result = await getattr(device, method)(**kwargs)

    assert asdict(result) == snapshot


async def test_generation_differences(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the fields that only one of the generations reports."""
    for generation in GENERATIONS:
        for path, method in (("display", "display"), ("audio", "audio")):
            responses.get(
                f"{DEVICE_URL}/api/v2/device/{path}",
                status=200,
                body=load_fixture(f"{method}_{generation}.json"),
            )

    old_display = await device.display()
    old_audio = await device.audio()
    new_display = await device.display()
    new_audio = await device.audio()

    # Firmware 2.x does not report whether the display is on.
    assert old_display.on is None
    assert new_display.on is True

    # Firmware 3.x reports whether the device has audio at all.
    assert "available" not in load_fixture("audio_lm37x8.json")
    assert new_audio.available is True
    assert old_audio.available is True


async def test_bluetooth_reports_address_and_mac(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test firmware 3.x, which sends both names for the address, parses."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/bluetooth",
        status=200,
        body=load_fixture("bluetooth_sa8.json"),
    )

    bluetooth = await device.bluetooth()

    assert '"address"' in load_fixture("bluetooth_sa8.json")
    assert '"mac"' in load_fixture("bluetooth_sa8.json")
    assert bluetooth.address == "AA:BB:CC:DD:EE:FF"


async def test_notification_not_found(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test asking for a notification that is not in the queue."""
    responses.get(
        f"{DEVICE_URL}/api/v2/device/notifications/999999",
        status=404,
        body='{ "errors" : [ { "message" : "Notification not found" } ] }',
    )

    with pytest.raises(LaMetricError, match=r"\(404\): Notification not found"):
        await device.notification(notification_id=999999)
