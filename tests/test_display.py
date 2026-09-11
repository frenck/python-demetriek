"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
from datetime import time

import aiohttp
import pytest
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricDevice
from demetriek.const import BrightnessMode, DisplayType, ScreensaverMode

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
    assert display.screensaver
    assert display.screensaver.enabled is False
    assert display.screensaver.widget == "08b8eac21074f8f7e5a29f2855ba8060"
    assert display.screensaver.modes
    assert display.screensaver.modes.when_dark.enabled is False
    assert display.screensaver.modes.time_based.enabled is True
    assert display.screensaver.modes.time_based.start_time == time(0, 0, 39)
    assert display.screensaver.modes.time_based.end_time is None
    assert display.screensaver.modes.time_based.local_start_time == time(1, 0, 39)
    assert display.screensaver.modes.time_based.local_end_time is None


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


async def test_set_display_screensaver_mode(aresponses: ResponsesMockServer) -> None:
    """Test setting the time based screensaver mode."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "screensaver": {
                "enabled": True,
                "mode": "time_based",
                "mode_params": {
                    "enabled": True,
                    "start_time": "23:00:00",
                    "end_time": "07:00:00",
                },
            },
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("display_set_screensaver.json"),
        )

    aresponses.add("127.0.0.2:4343", "/api/v2/device/display", "PUT", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        display = await demetriek.display(
            screensaver_enabled=True,
            screensaver_mode=ScreensaverMode.TIME_BASED,
            screensaver_mode_enabled=True,
            screensaver_start_time=time(23, 0, 0),
            screensaver_end_time=time(7, 0, 0),
        )

    assert display.screensaver
    assert display.screensaver.modes
    assert display.screensaver.modes.time_based.enabled is True
    assert display.screensaver.modes.time_based.start_time == time(23, 0, 0)
    assert display.screensaver.modes.time_based.end_time == time(7, 0, 0)
    assert display.screensaver.modes.time_based.local_start_time == time(1, 0, 0)
    assert display.screensaver.modes.time_based.local_end_time == time(9, 0, 0)
    # Enabling one mode disables the other on the device.
    assert display.screensaver.modes.when_dark.enabled is False


async def test_set_display_screensaver_mode_without_params(
    aresponses: ResponsesMockServer,
) -> None:
    """Test selecting a screensaver mode without any mode parameters."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {"screensaver": {"mode": "when_dark"}}
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("display_set_screensaver.json"),
        )

    aresponses.add("127.0.0.2:4343", "/api/v2/device/display", "PUT", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.display(screensaver_mode=ScreensaverMode.WHEN_DARK)


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        (time(23, 0, 0), None),
        (None, time(7, 0, 0)),
        (None, None),
    ],
)
async def test_set_display_screensaver_time_based_needs_both_times(
    start_time: time | None,
    end_time: time | None,
) -> None:
    """Test the time based mode is rejected without both of its times."""
    demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc")
    with pytest.raises(ValueError, match="needs both"):
        await demetriek.display(
            screensaver_mode=ScreensaverMode.TIME_BASED,
            screensaver_mode_enabled=True,
            screensaver_start_time=start_time,
            screensaver_end_time=end_time,
        )


async def test_set_display_screensaver_when_dark_needs_no_times(
    aresponses: ResponsesMockServer,
) -> None:
    """Test the other modes are unaffected by the time based requirement."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        assert await request.json() == {
            "screensaver": {"mode": "when_dark", "mode_params": {"enabled": True}},
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("display_set_screensaver.json"),
        )

    aresponses.add("127.0.0.2:4343", "/api/v2/device/display", "PUT", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.display(
            screensaver_mode=ScreensaverMode.WHEN_DARK,
            screensaver_mode_enabled=True,
        )
