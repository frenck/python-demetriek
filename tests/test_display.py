"""Asynchronous Python client for LaMetric TIME devices."""

from datetime import time

import pytest
from aioresponses import aioresponses

from demetriek import LaMetricDevice
from demetriek.const import BrightnessMode, DisplayType, ScreensaverMode

from .conftest import DEVICE_URL, load_fixture, request_json

DISPLAY_URL = f"{DEVICE_URL}/api/v2/device/display"


async def test_get_display(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting display information."""
    responses.get(DISPLAY_URL, status=200, body=load_fixture("display.json"))

    display = await device.display()

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
    assert display.screensaver.modes.when_dark
    assert display.screensaver.modes.when_dark.enabled is False
    assert display.screensaver.modes.time_based.enabled is True
    assert display.screensaver.modes.time_based.start_time == time(0, 0, 39)
    assert display.screensaver.modes.time_based.end_time is None
    assert display.screensaver.modes.time_based.local_start_time == time(1, 0, 39)
    assert display.screensaver.modes.time_based.local_end_time is None


async def test_set_display(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test setting display properties."""
    responses.put(DISPLAY_URL, status=200, body=load_fixture("display_set.json"))

    display = await device.display(
        brightness=99,
        brightness_mode=BrightnessMode.MANUAL,
        screensaver_enabled=False,
        on=True,
    )

    assert request_json(responses, "PUT", DISPLAY_URL) == {
        "brightness": 99,
        "brightness_mode": "manual",
        "screensaver": {
            "enabled": False,
        },
        "on": True,
    }
    assert display
    assert display.brightness == 99
    assert display.brightness_mode is BrightnessMode.MANUAL
    assert display.width == 37
    assert display.height == 8
    assert display.display_type is DisplayType.MIXED
    assert display.screensaver
    assert display.screensaver.enabled is False
    assert display.on is True


async def test_set_display_zero_and_off(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test zero and off are sent, and not mistaken for no value at all."""
    responses.put(DISPLAY_URL, status=200, body=load_fixture("display_set.json"))

    await device.display(brightness=0, screensaver_enabled=False, on=False)

    assert request_json(responses, "PUT", DISPLAY_URL) == {
        "brightness": 0,
        "screensaver": {"enabled": False},
        "on": False,
    }


async def test_set_display_screensaver_mode(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test setting the time based screensaver mode."""
    responses.put(
        DISPLAY_URL, status=200, body=load_fixture("display_set_screensaver.json")
    )

    display = await device.display(
        screensaver_enabled=True,
        screensaver_mode=ScreensaverMode.TIME_BASED,
        screensaver_mode_enabled=True,
        screensaver_start_time=time(23, 0, 0),
        screensaver_end_time=time(7, 0, 0),
    )

    assert request_json(responses, "PUT", DISPLAY_URL) == {
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
    assert display.screensaver
    assert display.screensaver.modes
    assert display.screensaver.modes.time_based.enabled is True
    assert display.screensaver.modes.time_based.start_time == time(23, 0, 0)
    assert display.screensaver.modes.time_based.end_time == time(7, 0, 0)
    assert display.screensaver.modes.time_based.local_start_time == time(1, 0, 0)
    assert display.screensaver.modes.time_based.local_end_time == time(9, 0, 0)
    # Enabling one mode disables the other on the device.
    assert display.screensaver.modes.when_dark
    assert display.screensaver.modes.when_dark.enabled is False


async def test_set_display_screensaver_mode_without_params(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test selecting a screensaver mode without any mode parameters."""
    responses.put(
        DISPLAY_URL, status=200, body=load_fixture("display_set_screensaver.json")
    )

    await device.display(screensaver_mode=ScreensaverMode.WHEN_DARK)

    assert request_json(responses, "PUT", DISPLAY_URL) == {
        "screensaver": {"mode": "when_dark"}
    }


async def test_set_display_screensaver_screen_off(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test selecting the screen off screensaver mode, which a SKY reports."""
    responses.put(
        DISPLAY_URL, status=200, body=load_fixture("display_set_screensaver.json")
    )

    await device.display(
        screensaver_mode=ScreensaverMode.SCREEN_OFF,
        screensaver_mode_enabled=True,
    )

    assert request_json(responses, "PUT", DISPLAY_URL) == {
        "screensaver": {"mode": "screen_off", "mode_params": {"enabled": True}}
    }


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
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the other modes are unaffected by the time based requirement."""
    responses.put(
        DISPLAY_URL, status=200, body=load_fixture("display_set_screensaver.json")
    )

    await device.display(
        screensaver_mode=ScreensaverMode.WHEN_DARK,
        screensaver_mode_enabled=True,
    )

    assert request_json(responses, "PUT", DISPLAY_URL) == {
        "screensaver": {"mode": "when_dark", "mode_params": {"enabled": True}},
    }
