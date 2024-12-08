"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import aiohttp
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricDevice

from . import load_fixture


async def test_get_bluetooth(aresponses: ResponsesMockServer) -> None:
    """Test getting bluetooth information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/bluetooth",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("bluetooth.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        bluetooth = await demetriek.bluetooth()

    assert bluetooth
    assert bluetooth.active is True
    assert bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert bluetooth.available is True
    assert bluetooth.discoverable is True
    assert bluetooth.name == "LM1234"
    assert bluetooth.pairable is True


async def test_set_audio(aresponses: ResponsesMockServer) -> None:
    """Test setting display properties."""

    async def response_handler(request: aiohttp.ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "active": False,
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("bluetooth_set.json"),
        )

    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/bluetooth",
        "PUT",
        response_handler,
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        bluetooth = await demetriek.bluetooth(active=False)

    assert bluetooth
    assert bluetooth.active is False
    assert bluetooth.address == "AA:BB:CC:DD:EE:FF"
    assert bluetooth.available is True
    assert bluetooth.discoverable is True
    assert bluetooth.name == "LM1234"
    assert bluetooth.pairable is True
