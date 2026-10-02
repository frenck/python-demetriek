"""Asynchronous Python client for LaMetric TIME devices."""

from aioresponses import aioresponses

from demetriek import LaMetricDevice

from .conftest import DEVICE_URL, load_fixture, request_json

BLUETOOTH_URL = f"{DEVICE_URL}/api/v2/device/bluetooth"


async def test_get_bluetooth(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting bluetooth information."""
    responses.get(BLUETOOTH_URL, status=200, body=load_fixture("bluetooth.json"))

    bluetooth = await device.bluetooth()

    assert bluetooth
    assert bluetooth.active is True
    assert bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert bluetooth.available is True
    assert bluetooth.discoverable is True
    assert bluetooth.name == "LM1234"
    assert bluetooth.pairable is True


async def test_set_bluetooth(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test setting bluetooth properties."""
    responses.put(BLUETOOTH_URL, status=200, body=load_fixture("bluetooth_set.json"))

    bluetooth = await device.bluetooth(active=False)

    assert request_json(responses, "PUT", BLUETOOTH_URL) == {"active": False}
    assert bluetooth
    assert bluetooth.active is False
    assert bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert bluetooth.available is True
    assert bluetooth.discoverable is True
    assert bluetooth.name == "LM1234"
    assert bluetooth.pairable is True


async def test_get_bluetooth_keeps_address(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test an address sent by the device is not overwritten."""
    responses.get(
        BLUETOOTH_URL,
        status=200,
        body=(
            '{"active": true, "address": "11:22:33:44:55:66", "available": true,'
            ' "discoverable": true, "name": "LM1234", "pairable": true}'
        ),
    )

    bluetooth = await device.bluetooth()

    assert bluetooth.address == "11:22:33:44:55:66"


async def test_set_bluetooth_name(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test changing the Bluetooth name."""
    responses.put(BLUETOOTH_URL, status=200, body=load_fixture("bluetooth_set.json"))

    await device.bluetooth(active=True, name="Living room")

    assert request_json(responses, "PUT", BLUETOOTH_URL) == {
        "active": True,
        "name": "Living room",
    }
