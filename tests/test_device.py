"""Asynchronous Python client for LaMetric TIME devices."""
# pylint: disable=protected-access
from ipaddress import IPv4Address

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from demetriek import LaMetricDevice
from demetriek.const import BrightnessMode, DeviceMode, DisplayType, WifiMode

from . import load_fixture


@pytest.mark.asyncio
async def test_get_device(aresponses: ResponsesMockServer) -> None:
    """Test getting device information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        device = await demetriek.device()

    assert device
    assert device.device_id == "12345"
    assert device.name == "Frenck's LaMetric"
    assert device.os_version == "2.2.2"
    assert device.mode is DeviceMode.AUTO
    assert device.model == "LM 37X8"
    assert device.audio.volume == 100
    assert device.audio.volume_range
    assert device.audio.volume_range.range_min == 0
    assert device.audio.volume_range.range_max == 100
    assert device.audio.volume_limit
    assert device.audio.volume_limit.range_min == 0
    assert device.audio.volume_limit.range_max == 100
    assert device.bluetooth.available is True
    assert device.bluetooth.name == "LM1234"
    assert device.bluetooth.active is False
    assert device.bluetooth.discoverable is True
    assert device.bluetooth.pairable is True
    assert device.bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert device.display.brightness == 100
    assert device.display.brightness_mode is BrightnessMode.AUTO
    assert device.display.width == 37
    assert device.display.height == 8
    assert device.display.display_type is DisplayType.MIXED
    assert device.display.screensaver.enabled is False
    assert device.wifi.active is True
    assert device.wifi.available is True
    assert device.wifi.mac == "AA:BB:CC:DD:EE:FF"
    assert device.wifi.encryption == "WPA"
    assert device.wifi.ssid == "Frenck"
    assert device.wifi.ip == IPv4Address("192.168.1.11")
    assert device.wifi.mode is WifiMode.DHCP
    assert device.wifi.netmask == "255.255.255.0"
    assert device.wifi.rssi == 21


@pytest.mark.asyncio
async def test_get_device2(aresponses: ResponsesMockServer) -> None:
    """Test getting device information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device2.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        device = await demetriek.device()

    assert device
    assert device.device_id == "12345"
    assert device.name == "Frenck's LaMetric"
    assert device.os_version == "2.2.2"
    assert device.mode is DeviceMode.SCHEDULE
    assert device.model == "LM 37X8"
    assert device.audio.volume == 100
    assert device.audio.volume_range
    assert device.audio.volume_range.range_min == 0
    assert device.audio.volume_range.range_max == 100
    assert device.audio.volume_limit
    assert device.audio.volume_limit.range_min == 0
    assert device.audio.volume_limit.range_max == 100
    assert device.bluetooth.available is True
    assert device.bluetooth.name == "LM1234"
    assert device.bluetooth.active is False
    assert device.bluetooth.discoverable is True
    assert device.bluetooth.pairable is True
    assert device.bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert device.display.brightness == 100
    assert device.display.brightness_mode is BrightnessMode.AUTO
    assert device.display.width == 37
    assert device.display.height == 8
    assert device.display.display_type is DisplayType.MIXED
    assert device.wifi.active is True
    assert device.wifi.available is True
    assert device.wifi.mac == "AA:BB:CC:DD:EE:FF"
    assert device.wifi.encryption is None
    assert device.wifi.ssid == "Frenck"
    assert device.wifi.ip == IPv4Address("192.168.1.11")
    assert device.wifi.mode is WifiMode.DHCP
    assert device.wifi.netmask == "255.255.255.0"
    assert device.wifi.rssi is None
