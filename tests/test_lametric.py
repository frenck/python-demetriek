"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
import socket
from unittest.mock import MagicMock

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
from demetriek.exceptions import error_message

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


def test_repr_hides_api_key() -> None:
    """Test the API key does not leak when the client is printed or logged."""
    demetriek = LaMetricDevice(host="127.0.0.2", api_key="supersecret")

    assert "supersecret" not in repr(demetriek)


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


@pytest.mark.parametrize(
    "exception",
    [
        TimeoutError(),
        aiohttp.ServerDisconnectedError(),
    ],
)
async def test_change_not_retried_once_sent(
    responses: aioresponses, device: LaMetricDevice, exception: Exception
) -> None:
    """Test a change is not repeated when it may have reached the device.

    Repeating it could, for example, show the same notification twice.
    """
    responses.post(f"{DEVICE_URL}/", exception=exception, repeat=True)

    with pytest.raises(LaMetricConnectionError):
        await device._request("/", method="POST")

    assert len(next(iter(responses.requests.values()))) == 1


@pytest.mark.parametrize(
    "exception",
    [
        aiohttp.ClientConnectorError(MagicMock(), OSError()),
        socket.gaierror(),
    ],
)
async def test_change_retried_when_not_sent(
    responses: aioresponses, device: LaMetricDevice, exception: Exception
) -> None:
    """Test a change is retried when it never reached the device."""
    responses.post(f"{DEVICE_URL}/", exception=exception)
    responses.post(f"{DEVICE_URL}/", exception=exception)
    responses.post(f"{DEVICE_URL}/", status=200, body='{"status": "ok"}')

    response = await device._request("/", method="POST")

    assert response["status"] == "ok"


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


async def test_http_error_message(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the error message of the device is passed on."""
    responses.post(
        f"{DEVICE_URL}/",
        status=400,
        body='{ "errors" : [ { "message" : "Missing required keys [frames]" } ] }',
    )

    with pytest.raises(
        LaMetricError, match=r"\(400\): Missing required keys \[frames\]"
    ):
        await device._request("/", method="POST", data={"nope": True})

    # The device answered, so there is nothing to retry.
    assert len(next(iter(responses.requests.values()))) == 1


async def test_http_error_without_message(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the HTTP reason is used when the device gives no message."""
    responses.get(
        f"{DEVICE_URL}/",
        status=404,
        body="OMG PUPPIES!",
        content_type="text/plain",
        reason="Not Found",
    )

    with pytest.raises(LaMetricError, match=r"\(404\): Not Found"):
        await device._request("/")


async def test_http_error401_message(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test the authentication error carries the message of the device."""
    responses.get(
        f"{DEVICE_URL}/",
        status=401,
        body='{"errors":[{"message":"Authorization is required"}]}',
    )

    with pytest.raises(
        LaMetricAuthenticationError, match="failed: Authorization is required"
    ):
        await device._request("/")


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ('{"errors": [{"message": "Forbidden"}]}', "Forbidden"),
        ('{"errors": [{"message": "One"}, {"message": "Two"}]}', "One; Two"),
        ('{"errors": [{"code": 1}, "nonsense"]}', None),
        ('{"errors": "nonsense"}', None),
        ('{"errors": []}', None),
        ('["errors"]', None),
        ("OMG PUPPIES!", None),
        ("", None),
    ],
)
def test_error_message(body: str, expected: str | None) -> None:
    """Test the error messages are pulled out of an error response."""
    assert error_message(body) == expected
