"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import aiohttp
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricDevice

from . import load_fixture


async def test_get_audio(aresponses: ResponsesMockServer) -> None:
    """Test getting audio information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/audio",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("audio.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        audio = await demetriek.audio()

    assert audio
    assert audio.volume == 50
    assert audio.volume_range
    assert audio.volume_range.range_min == 0
    assert audio.volume_range.range_max == 100
    assert audio.volume_limit
    assert audio.volume_limit.range_min == 0
    assert audio.volume_limit.range_max == 100


async def test_set_audio(aresponses: ResponsesMockServer) -> None:
    """Test setting display properties."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "volume": 99,
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("audio_set.json"),
        )

    aresponses.add("127.0.0.2:4343", "/api/v2/device/audio", "PUT", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        audio = await demetriek.audio(volume=99)

    assert audio
    assert audio.volume == 99
    assert audio.volume_range
    assert audio.volume_range.range_min == 0
    assert audio.volume_range.range_max == 100
    assert audio.volume_limit
    assert audio.volume_limit.range_min == 0
    assert audio.volume_limit.range_max == 100
