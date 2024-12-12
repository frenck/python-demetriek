"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
from ipaddress import IPv4Address

import aiohttp
from aresponses import ResponsesMockServer

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
from demetriek.const import (
    BrightnessMode,
    DeviceMode,
    DisplayType,
    NotificationType,
    WifiMode,
)

from . import load_fixture


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
    assert device.audio
    assert device.audio.volume == 100
    assert device.audio.volume_range
    assert device.audio.volume_range.range_min == 0
    assert device.audio.volume_range.range_max == 100
    assert device.audio.volume_limit
    assert device.audio.volume_limit.range_min == 0
    assert device.audio.volume_limit.range_max == 100
    assert device.bluetooth
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
    assert device.display.screensaver
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
    assert device.audio
    assert device.audio.volume == 100
    assert device.audio.volume_range
    assert device.audio.volume_range.range_min == 0
    assert device.audio.volume_range.range_max == 100
    assert device.audio.volume_limit
    assert device.audio.volume_limit.range_min == 0
    assert device.audio.volume_limit.range_max == 100
    assert device.bluetooth
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


async def test_notify(aresponses: ResponsesMockServer) -> None:
    """Test sending notification serialization."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/notifications",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("notification.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
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
        response = await demetriek.notify(notification=notification)

    # check response
    assert response == 1
    # check on serialized request if aliases are used and null values are removed
    request = await aresponses.history[0].request.json()
    assert request["type"] == "external"
    assert request["icon_type"] == "alert"
    assert "life_time" not in request
    assert request["model"]["sound"]["id"] == "win"
    assert request["model"]["sound"]["category"] == "notifications"
    assert request["model"]["frames"][0]["text"] == "Yeah"
    assert request["model"]["frames"][1]["goalData"]["current"] == 65
    assert request["model"]["frames"][2]["chartData"] == [1, 2, 3, 4, 5, 4, 3, 2, 1]
