"""Asynchronous Python client for LaMetric TIME devices."""

from aioresponses import aioresponses

from demetriek import LaMetricDevice

from .conftest import DEVICE_URL, load_fixture, request_json

AUDIO_URL = f"{DEVICE_URL}/api/v2/device/audio"


async def test_get_audio(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting audio information."""
    responses.get(AUDIO_URL, status=200, body=load_fixture("audio.json"))

    audio = await device.audio()

    assert audio
    assert audio.volume == 50
    assert audio.volume_range
    assert audio.volume_range.range_min == 0
    assert audio.volume_range.range_max == 100
    assert audio.volume_limit
    assert audio.volume_limit.range_min == 0
    assert audio.volume_limit.range_max == 100


async def test_set_audio(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test setting audio properties."""
    responses.put(AUDIO_URL, status=200, body=load_fixture("audio_set.json"))

    audio = await device.audio(volume=99)

    assert request_json(responses, "PUT", AUDIO_URL) == {"volume": 99}
    assert audio
    assert audio.volume == 99
    assert audio.volume_range
    assert audio.volume_range.range_min == 0
    assert audio.volume_range.range_max == 100
    assert audio.volume_limit
    assert audio.volume_limit.range_min == 0
    assert audio.volume_limit.range_max == 100
