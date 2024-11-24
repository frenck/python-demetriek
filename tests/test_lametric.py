"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import asyncio

import aiohttp
import pytest
from aresponses import Response, ResponsesMockServer

from demetriek import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricDevice,
    LaMetricError,
)


async def test_json_request(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        response = await demetriek._request("/")
        assert response["status"] == "ok"


async def test_internal_session(aresponses: ResponsesMockServer) -> None:
    """Test JSON response is handled correctly."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with LaMetricDevice(host="127.0.0.2", api_key="abc") as demetriek:
        response = await demetriek._request("/")
        assert response["status"] == "ok"


async def test_post_request(aresponses: ResponsesMockServer) -> None:
    """Test POST requests are handled correctly."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        response = await demetriek._request("/", method="POST")
        assert response["status"] == "ok"


async def test_backoff(aresponses: ResponsesMockServer) -> None:
    """Test requests are handled with retries."""

    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        response_handler,
        repeat=2,
    )
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(
            host="127.0.0.2",
            api_key="abc",
            session=session,
            request_timeout=0.1,
        )
        response = await demetriek._request("/")
        assert response["status"] == "ok"


async def test_timeout(aresponses: ResponsesMockServer) -> None:
    """Test request timeouts."""

    # Faking a timeout by sleeping
    async def response_handler(_: aiohttp.ClientResponse) -> Response:
        await asyncio.sleep(0.2)
        return aresponses.Response(body="Goodmorning!")

    # Backoff will try 3 times
    aresponses.add("127.0.0.2:4343", "/", "GET", response_handler)
    aresponses.add("127.0.0.2:4343", "/", "GET", response_handler)
    aresponses.add("127.0.0.2:4343", "/", "GET", response_handler)

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(
            host="127.0.0.2",
            api_key="abc",
            session=session,
            request_timeout=0.1,
        )
        with pytest.raises(LaMetricConnectionError):
            assert await demetriek._request("/")


async def test_http_error400(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 404 response handling."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(text="OMG PUPPIES!", status=404),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="example.com", api_key="abc", session=session)
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


async def test_http_error500(aresponses: ResponsesMockServer) -> None:
    """Test HTTP 500 response handling."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(
            body=b'{"status":"nok"}',
            status=500,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice("127.0.0.2", api_key="abc", session=session)
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


async def test_no_json_response(aresponses: ResponsesMockServer) -> None:
    """Test response handling when its not a JSON response."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(
            body=b"Oh hi!",
            status=200,
            headers={"Content-Type": "text/html"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice("127.0.0.2", api_key="abc", session=session)
        with pytest.raises(LaMetricError):
            assert await demetriek._request("/")


@pytest.mark.parametrize("status", {401, 403})
async def test_http_error401(aresponses: ResponsesMockServer, status: int) -> None:
    """Test HTTP 401 response handling."""
    aresponses.add(
        "127.0.0.2:4343",
        "/",
        "GET",
        aresponses.Response(text="Access denied!", status=status),
    )

    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice("127.0.0.2", api_key="abc", session=session)
        with pytest.raises(LaMetricAuthenticationError):
            assert await demetriek._request("/")
