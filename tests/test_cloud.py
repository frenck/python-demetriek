"""Asynchronous Python client for LaMetric TIME devices."""

# pylint: disable=protected-access
from datetime import UTC, datetime
from ipaddress import IPv4Address

import aiohttp
import pytest
from aioresponses import aioresponses

from demetriek import (
    CloudDevice,
    LaMetricAuthenticationError,
    LaMetricCloud,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
    User,
)
from demetriek.const import DeviceState

from .conftest import CLOUD_URL, load_fixture, request_json


async def test_json_request(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test JSON response is handled correctly."""
    responses.get(f"{CLOUD_URL}/", status=200, body='{"status": "ok"}')

    response = await cloud._request("/")
    assert response["status"] == "ok"


async def test_internal_session(responses: aioresponses) -> None:
    """Test the client creates and closes its own session."""
    responses.get(f"{CLOUD_URL}/", status=200, body='{"status": "ok"}')

    async with LaMetricCloud(token="abc") as demetriek:  # noqa: S106
        response = await demetriek._request("/")
        assert response["status"] == "ok"


def test_repr_hides_token() -> None:
    """Test the token does not leak when the client is printed or logged."""
    demetriek = LaMetricCloud(token="supersecret")  # noqa: S106

    assert "supersecret" not in repr(demetriek)


async def test_request_auth(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test the token is sent as a bearer token."""
    responses.get(f"{CLOUD_URL}/", status=200, body="{}")

    await cloud._request("/")

    request = next(iter(responses.requests.values()))[0]
    assert request.kwargs["headers"]["Authorization"] == "Bearer abc"
    assert request.kwargs["headers"]["Accept"] == "application/json"


async def test_retries(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test connection errors are retried before giving up."""
    responses.get(f"{CLOUD_URL}/", exception=aiohttp.ClientError())
    responses.get(f"{CLOUD_URL}/", exception=aiohttp.ClientError())
    responses.get(f"{CLOUD_URL}/", status=200, body='{"status": "ok"}')

    response = await cloud._request("/")
    assert response["status"] == "ok"


async def test_connection_error(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test a connection error is raised once all retries are used up."""
    responses.get(f"{CLOUD_URL}/", exception=aiohttp.ClientError(), repeat=True)

    with pytest.raises(LaMetricConnectionError):
        await cloud._request("/")

    assert len(next(iter(responses.requests.values()))) == 3


async def test_timeout(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test request timeouts are retried, then raised."""
    responses.get(f"{CLOUD_URL}/", exception=TimeoutError(), repeat=True)

    with pytest.raises(LaMetricConnectionTimeoutError):
        await cloud._request("/")

    assert len(next(iter(responses.requests.values()))) == 3


async def test_http_error404(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test HTTP 404 response handling."""
    responses.get(
        f"{CLOUD_URL}/",
        status=404,
        body="OMG PUPPIES!",
        content_type="text/plain",
    )

    with pytest.raises(LaMetricError):
        await cloud._request("/")


async def test_http_error500(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test HTTP 500 response handling."""
    responses.get(f"{CLOUD_URL}/", status=500, body='{"status":"nok"}')

    with pytest.raises(LaMetricError):
        await cloud._request("/")


@pytest.mark.parametrize("status", [401, 403])
async def test_http_error401(
    responses: aioresponses, cloud: LaMetricCloud, status: int
) -> None:
    """Test an invalid or expired token raises an authentication error."""
    responses.get(
        f"{CLOUD_URL}/",
        status=status,
        body='{"errors":[{"message":"Unauthorized"}]}',
        repeat=True,
    )

    with pytest.raises(LaMetricAuthenticationError, match="failed: Unauthorized"):
        await cloud._request("/")

    # Retrying a rejected token is pointless, it must fail right away.
    assert len(next(iter(responses.requests.values()))) == 1


async def test_http_error_not_retried(
    responses: aioresponses, cloud: LaMetricCloud
) -> None:
    """Test an HTTP error is not mistaken for a connection error."""
    responses.get(f"{CLOUD_URL}/", status=500, body='{"status":"nok"}', repeat=True)

    with pytest.raises(LaMetricError) as excinfo:
        await cloud._request("/")

    assert not isinstance(excinfo.value, LaMetricConnectionError)
    assert len(next(iter(responses.requests.values()))) == 1


async def test_no_json_response(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test response handling when it is not a JSON response."""
    responses.get(
        f"{CLOUD_URL}/",
        status=200,
        body="Oh hi!",
        content_type="text/html",
    )

    with pytest.raises(LaMetricError, match="'text/html', instead of JSON"):
        await cloud._request("/")


async def test_invalid_json_response(
    responses: aioresponses, cloud: LaMetricCloud
) -> None:
    """Test a broken JSON response raises a LaMetricError, without retrying."""
    responses.get(f"{CLOUD_URL}/", status=200, body="{", repeat=True)

    with pytest.raises(LaMetricError, match="invalid JSON"):
        await cloud._request("/")

    assert len(next(iter(responses.requests.values()))) == 1


async def test_get_current_user(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test getting current logged in user information."""
    responses.get(
        f"{CLOUD_URL}/api/v2/users/me", status=200, body=load_fixture("me.json")
    )

    user = await cloud.current_user()

    assert user
    assert user.apps_count == 1
    assert user.email == "opensource@frenck.dev"
    assert user.name == "Franck Nijhof"
    assert user.private_apps_count == 3
    assert user.private_device_count == 5
    assert user.user_id == 1
    assert User.from_dict(user.to_dict()) == user


async def test_get_devices(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test getting devices from the logged in account."""
    responses.get(
        f"{CLOUD_URL}/api/v2/users/me/devices",
        status=200,
        body=load_fixture("cloud_devices.json"),
    )

    devices = await cloud.devices()

    assert devices
    assert len(devices) == 2
    assert devices[0].device_id == 21
    assert devices[0].name == "Blackjack"
    assert devices[0].state == DeviceState.CONFIGURED
    assert devices[0].product_code == "sa1"
    assert devices[0].serial_number == "SA140100002200W00B21"
    assert (
        devices[0].api_key
        == "8adaa0c98278dbb1ecb218d1c3e11f9312317ba474ab3361f80c0bd4f13a6721"
    )
    assert devices[0].ip == IPv4Address("192.168.1.21")
    assert devices[0].mac == "AA:BB:CC:DD:EE:21"
    assert devices[0].ssid == "AllYourBaseAreBelongToUs"
    assert devices[0].created_at == datetime(
        2015,
        3,
        6,
        15,
        15,
        55,
        tzinfo=UTC,
    )
    assert devices[0].updated_at == datetime(
        2016,
        6,
        14,
        18,
        27,
        13,
        tzinfo=UTC,
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
        2015,
        3,
        6,
        15,
        15,
        55,
        tzinfo=UTC,
    )
    assert devices[1].updated_at == datetime(
        2016,
        6,
        14,
        18,
        27,
        13,
        tzinfo=UTC,
    )


async def test_get_device(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test getting a specific device from the logged in account."""
    responses.get(
        f"{CLOUD_URL}/api/v2/users/me/devices/42",
        status=200,
        body=load_fixture("cloud_device.json"),
    )

    device = await cloud.device(device_id=42)

    assert device
    assert device.device_id == 42
    assert device.name == "The Answer"
    assert device.state is None
    assert device.product_code is None
    assert device.serial_number == "SA140100002200W00B42"
    assert (
        device.api_key
        == "8adaa0c98278dbb1ecb218d1c3e11f9312317ba474ab3361f80c0bd4f13a6742"
    )
    assert device.ip == IPv4Address("192.168.1.42")
    assert device.mac == "AA:BB:CC:DD:EE:42"
    assert device.ssid == "AllYourBaseAreBelongToUs"
    assert device.created_at == datetime(2015, 3, 6, 15, 15, 55, tzinfo=UTC)
    assert device.updated_at == datetime(2016, 6, 14, 18, 27, 13, tzinfo=UTC)
    assert CloudDevice.from_dict(device.to_dict()) == device
    assert device.api_key not in repr(device)


async def test_rename_device(responses: aioresponses, cloud: LaMetricCloud) -> None:
    """Test renaming a device."""
    url = f"{CLOUD_URL}/api/v2/users/me/devices/42"
    responses.put(url, status=200, body=load_fixture("cloud_device_rename.json"))

    await cloud.rename_device(42, name="Device @ Work")

    assert request_json(responses, "PUT", url) == {"name": "Device @ Work"}


async def test_rename_device_without_scope(
    responses: aioresponses, cloud: LaMetricCloud
) -> None:
    """Test renaming without the devices_write scope raises an auth error."""
    responses.put(
        f"{CLOUD_URL}/api/v2/users/me/devices/42",
        status=403,
        body='{"errors":[{"message":"Forbidden"}]}',
    )

    with pytest.raises(LaMetricAuthenticationError):
        await cloud.rename_device(42, name="Device @ Work")
