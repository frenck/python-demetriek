"""Asynchronous Python client for LaMetric TIME devices."""
# pylint: disable=protected-access
from ipaddress import IPv4Address

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from demetriek import LaMetricDevice
from demetriek.const import WifiMode

from . import load_fixture


@pytest.mark.asyncio
async def test_get_wifi(aresponses: ResponsesMockServer) -> None:
    """Test getting audio information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/wifi",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("wifi.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        wifi = await demetriek.wifi()

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


@pytest.mark.asyncio
async def test_get_wifi2(aresponses: ResponsesMockServer) -> None:
    """Test getting audio information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/wifi",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("wifi2.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        wifi = await demetriek.wifi()

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
