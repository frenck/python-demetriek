"""Asynchronous Python client for LaMetric TIME devices."""

from ipaddress import IPv4Address

from aioresponses import aioresponses

from demetriek import LaMetricDevice
from demetriek.const import WifiMode

from .conftest import DEVICE_URL, load_fixture

WIFI_URL = f"{DEVICE_URL}/api/v2/device/wifi"


async def test_get_wifi(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting Wi-Fi information."""
    responses.get(WIFI_URL, status=200, body=load_fixture("wifi.json"))

    wifi = await device.wifi()

    assert wifi
    assert wifi.active is True
    assert wifi.mac == "AA:BB:CC:DD:EE:FF"
    assert wifi.available is True
    assert wifi.encryption == "WPA"
    assert wifi.ip == IPv4Address("192.168.1.2")
    assert wifi.mode == WifiMode.DHCP
    assert wifi.netmask == "255.255.255.0"
    assert wifi.ssid == "AllYourBaseAreBelongToUs"
    assert wifi.rssi == 42


async def test_get_wifi2(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting Wi-Fi information without encryption and signal strength."""
    responses.get(WIFI_URL, status=200, body=load_fixture("wifi2.json"))

    wifi = await device.wifi()

    assert wifi
    assert wifi.active is True
    assert wifi.mac == "AA:BB:CC:DD:EE:FF"
    assert wifi.available is True
    assert wifi.encryption is None
    assert wifi.ip == IPv4Address("192.168.1.2")
    assert wifi.mode == WifiMode.DHCP
    assert wifi.netmask == "255.255.255.0"
    assert wifi.ssid == "AllYourBaseAreBelongToUs"
    assert wifi.rssi is None


async def test_get_wifi_keeps_device_names(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test values sent under the device endpoint names are not overwritten."""
    responses.get(
        WIFI_URL,
        status=200,
        body=(
            '{"active": true, "available": true, "encryption": "WPA",'
            ' "ip": "192.168.1.3", "mac": "AA:BB:CC:DD:EE:FF", "mode": "dhcp",'
            ' "netmask": "255.255.255.0", "rssi": 77, "ssid": "Test"}'
        ),
    )

    wifi = await device.wifi()

    assert wifi.ip == IPv4Address("192.168.1.3")
    assert wifi.rssi == 77
