"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import aiohttp
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricDevice
from demetriek.const import BrightnessMode, DisplayType

from . import load_fixture


async def test_get_display(aresponses: ResponsesMockServer) -> None:
    """Test getting display information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/display",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("display.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        display = await demetriek.display()

    assert display
    assert display.brightness == 100
    assert display.brightness_limit
    assert display.brightness_limit.range_min == 2
    assert display.brightness_limit.range_max == 100
    assert display.brightness_range
    assert display.brightness_range.range_min == 0
    assert display.brightness_range.range_max == 100
    assert display.brightness_mode is BrightnessMode.AUTO
    assert display.width == 37
    assert display.height == 8
    assert display.display_type is DisplayType.MIXED
    assert display.on is True


async def test_set_display(aresponses: ResponsesMockServer) -> None:
    """Test setting display properties."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "brightness": 99,
            "brightness_mode": "manual",
            "screensaver": {
                "enabled": False,
            },
            "on": True,
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("display_set.json"),
        )

    aresponses.add("127.0.0.2:4343", "/api/v2/device/display", "PUT", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        display = await demetriek.display(
            brightness=99,
            brightness_mode=BrightnessMode.MANUAL,
            screensaver_enabled=False,
            on=True,
        )

    assert display
    assert display.brightness == 99
    assert display.brightness_mode is BrightnessMode.MANUAL
    assert display.width == 37
    assert display.height == 8
    assert display.display_type is DisplayType.MIXED
    assert display.screensaver
    assert display.screensaver.enabled is False
    assert display.on is True
