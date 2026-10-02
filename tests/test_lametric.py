"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import aiohttp
import pytest
from aioresponses import aioresponses

from demetriek import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricDevice,
    LaMetricError,
)

from .conftest import DEVICE_URL


async def test_json_request(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test JSON response is handled correctly."""
    responses.get(f"{DEVICE_URL}/", status=200, body='{"status": "ok"}')

    response = await device._request("/")
    assert response["status"] == "ok"


async def test_internal_session(responses: aioresponses) -> None:
    """Test the client creates and closes its own session."""
    responses.get(f"{DEVICE_URL}/", status=200, body='{"status": "ok"}')

    async with LaMetricDevice(host="127.0.0.2", api_key="abc") as demetriek:
        response = await demetriek._request("/")
        assert response["status"] == "ok"


async def test_post_request(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test POST requests are handled correctly."""
    responses.post(f"{DEVICE_URL}/", status=200, body='{"status": "ok"}')

    response = await device._request("/", method="POST")
    assert response["status"] == "ok"


async def test_request_auth(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test the API key is sent using basic authentication."""
    responses.get(f"{DEVICE_URL}/", status=200, body="{}")

    await device._request("/")

    request = next(iter(responses.requests.values()))[0]
    assert request.kwargs["auth"] == aiohttp.BasicAuth("dev", "abc")
    assert request.kwargs["headers"]["Accept"] == "application/json"


async def test_retries(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test connection errors are retried before giving up."""
    responses.get(f"{DEVICE_URL}/", exception=aiohttp.ClientError())
    responses.get(f"{DEVICE_URL}/", exception=aiohttp.ClientError())
    responses.get(f"{DEVICE_URL}/", status=200, body='{"status": "ok"}')

    response = await device._request("/")
    assert response["status"] == "ok"


async def test_connection_error(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test a connection error is raised once all retries are used up."""
    responses.get(f"{DEVICE_URL}/", exception=aiohttp.ClientError(), repeat=True)

    with pytest.raises(LaMetricConnectionError):
        await device._request("/")

    assert len(next(iter(responses.requests.values()))) == 3


async def test_timeout(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test request timeouts are retried, then raised."""
    responses.get(f"{DEVICE_URL}/", exception=TimeoutError(), repeat=True)

    with pytest.raises(LaMetricConnectionTimeoutError):
        await device._request("/")

    assert len(next(iter(responses.requests.values()))) == 3


async def test_http_error404(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test HTTP 404 response handling."""
    responses.get(
        f"{DEVICE_URL}/",
        status=404,
        body="OMG PUPPIES!",
        content_type="text/plain",
    )

    with pytest.raises(LaMetricError):
        await device._request("/")


async def test_http_error500(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test HTTP 500 response handling."""
    responses.get(f"{DEVICE_URL}/", status=500, body='{"status":"nok"}')

    with pytest.raises(LaMetricError):
        await device._request("/")


async def test_no_json_response(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test response handling when it is not a JSON response."""
    responses.get(
        f"{DEVICE_URL}/",
        status=200,
        body="Oh hi!",
        content_type="text/html",
    )

    with pytest.raises(LaMetricError):
        await device._request("/")


@pytest.mark.parametrize("status", [401, 403])
async def test_http_error401(
    responses: aioresponses, device: LaMetricDevice, status: int
) -> None:
    """Test HTTP 401 and 403 response handling."""
    responses.get(
        f"{DEVICE_URL}/",
        status=status,
        body="Access denied!",
        content_type="text/plain",
    )

    with pytest.raises(LaMetricAuthenticationError):
        await device._request("/")
