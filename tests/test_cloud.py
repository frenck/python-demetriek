"""Asynchronous Python client for LaMetric TIME devices."""
# pylint: disable=protected-access
import asyncio
from datetime import datetime, timezone
from ipaddress import IPv4Address

import aiohttp
import pytest
from aresponses import Response, ResponsesMockServer

from demetriek import LaMetricCloud, LaMetricConnectionError, LaMetricError
from demetriek.const import DeviceState

from . import load_fixture


@pytest.mark.asyncio
async def test_json_request(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        response = await demetriek._request("/")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with LaMetricCloud(token="abc") as demetriek:  # noqa: S106
        response = await demetriek._request("/")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_backoff(aresponses: ResponsesMockServer) -> None:
    """Test requests are handled with retries."""

    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        response_handler,
        repeat=2,
    )
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(  # noqa: S106
            token="abc", session=session, request_timeout=0.1
        )
        response = await demetriek._request("/")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeouts."""
    # Faking a timeout by sleeping
    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    # Backoff will try 3 times
    aresponses.add("developer.lametric.com", "/", "GET", response_handler)
    aresponses.add("developer.lametric.com", "/", "GET", response_handler)
    aresponses.add("developer.lametric.com", "/", "GET", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(  # noqa: S106
            token="abc", session=session, request_timeout=0.1
        )
        with pytest.raises(LaMetricConnectionError):
            assert await demetriek._request("/")


@pytest.mark.asyncio
async def test_http_error400(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 404 response handling."""
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(text="OMG PUPPIES!", status=404),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


@pytest.mark.asyncio
async def test_http_error500(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 500 response handling."""
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(
            body=b'{"status":"nok"}',
            status=500,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


@pytest.mark.asyncio
async def test_no_json_response(aresponses: ResponsesMockServer) -> None:
    """Test response handling when its not a JSON response."""
    aresponses.add(
        "developer.lametric.com",
        "/",
        "GET",
        aresponses.Response(
            body=b"Oh hi!",
            status=200,
            headers={"Content-Type": "text/html"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


@pytest.mark.asyncio
async def test_get_current_user(aresponses: ResponsesMockServer) -> None:
    """Test getting current logged in user information."""
    aresponses.add(
        "developer.lametric.com",
        "/api/v2/me",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("me.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        user = await demetriek.current_user()

    assert user
    assert user.apps_count == 1
    assert user.email == "opensource@frenck.dev"
    assert user.name == "Franck Nijhof"
    assert user.private_apps_count == 3
    assert user.private_device_count == 5
    assert user.user_id == 1


@pytest.mark.asyncio
async def test_get_devices(aresponses: ResponsesMockServer) -> None:
    """Test getting devices from the logged in account."""
    aresponses.add(
        "developer.lametric.com",
        "/api/v2/users/me/devices",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("cloud_devices.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        devices = await demetriek.devices()

    assert devices
    assert len(devices) == 2
    assert devices[0].device_id == 21
    assert devices[0].name == "Blackjack"
    assert devices[0].state == DeviceState.CONFIGURED
    assert devices[0].serial_number == "SA140100002200W00B21"
    assert (
        devices[0].api_key
        == "8adaa0c98278dbb1ecb218d1c3e11f9312317ba474ab3361f80c0bd4f13a6721"
    )
    assert devices[0].ip == IPv4Address("192.168.1.21")
    assert devices[0].mac == "AA:BB:CC:DD:EE:21"
    assert devices[0].ssid == "AllYourBaseAreBelongToUs"
    assert devices[0].created_at == datetime(
        2015, 3, 6, 15, 15, 55, tzinfo=timezone.utc
    )
    assert devices[0].updated_at == datetime(
        2016, 6, 14, 18, 27, 13, tzinfo=timezone.utc
    )

    assert devices[1].device_id == 42
    assert devices[1].name == "The Answer"
    assert devices[1].state == DeviceState.CONFIGURED
    assert devices[1].serial_number == "SA140100002200W00B42"
    assert (
        devices[1].api_key
        == "8adaa0c98278dbb1ecb218d1c3e11f9312317ba474ab3361f80c0bd4f13a6742"
    )
    assert devices[1].ip == IPv4Address("192.168.1.42")
    assert devices[1].mac == "AA:BB:CC:DD:EE:42"
    assert devices[1].ssid == "AllYourBaseAreBelongToUs"
    assert devices[1].created_at == datetime(
        2015, 3, 6, 15, 15, 55, tzinfo=timezone.utc
    )
    assert devices[1].updated_at == datetime(
        2016, 6, 14, 18, 27, 13, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_get_device(aresponses: ResponsesMockServer) -> None:
    """Test getting a specific device from the logged in account."""
    aresponses.add(
        "developer.lametric.com",
        "/api/v2/users/me/devices/42",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("cloud_device.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricCloud(token="abc", session=session)  # noqa: S106
        device = await demetriek.device(device_id=42)

    assert device
    assert device.device_id == 42
    assert device.name == "The Answer"
    assert device.state == DeviceState.CONFIGURED
    assert device.serial_number == "SA140100002200W00B42"
    assert (
        device.api_key
        == "8adaa0c98278dbb1ecb218d1c3e11f9312317ba474ab3361f80c0bd4f13a6742"
    )
    assert device.ip == IPv4Address("192.168.1.42")
    assert device.mac == "AA:BB:CC:DD:EE:42"
    assert device.ssid == "AllYourBaseAreBelongToUs"
    assert device.created_at == datetime(2015, 3, 6, 15, 15, 55, tzinfo=timezone.utc)
    assert device.updated_at == datetime(2016, 6, 14, 18, 27, 13, tzinfo=timezone.utc)
