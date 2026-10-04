"""Asynchronous Python client for LaMetric TIME devices.

The fixtures are answers of the web interface of a real sa8 TIME on
firmware 3.2.6, with the keys and IDs replaced.
"""

# pylint: disable=protected-access
import json

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from demetriek import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
    LaMetricLocalAuth,
)

from .conftest import load_fixture

WEB_URL = "https://127.0.0.2"
CHALLENGE_ID = "7b3636393566323030"
REQUEST_URL = f"{WEB_URL}/api/v1/user/request?group=web_admin"
CHALLENGE_URL = f"{WEB_URL}/api/v1/user/challenge/{CHALLENGE_ID}"
EXCHANGE_URL = f"{WEB_URL}/api/v1/user/request/exchange"
USERS_URL = f"{WEB_URL}/api/v1/user"


async def test_request_challenge(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test requesting a challenge, which the device shows on its screen."""
    responses.post(
        REQUEST_URL, status=200, body=load_fixture("auth_challenge_sa8.json")
    )

    challenge = await auth.request_challenge()

    assert challenge.challenge_id == CHALLENGE_ID
    assert challenge.duration == 60
    assert challenge.state == "in-progress"
    assert challenge.resolved is False
    assert ("POST", URL(REQUEST_URL)) in responses.requests


async def test_request_challenge_not_supported(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test a device without this flow, like an LM 37X8 TIME, says so.

    It asks for credentials instead, which is no reason to ask for new ones.
    """
    responses.post(
        REQUEST_URL,
        status=401,
        body='{"errors":[{"message":"Authorization is required"}]}',
    )

    with pytest.raises(LaMetricError, match="does not support") as error:
        await auth.request_challenge()

    assert error.type is LaMetricError


@pytest.mark.parametrize("body", ['{"nope": true}', "[]"])
async def test_request_challenge_unexpected_data(
    responses: aioresponses, auth: LaMetricLocalAuth, body: str
) -> None:
    """Test an answer that is no challenge raises a LaMetricError."""
    responses.post(REQUEST_URL, status=200, body=body)

    with pytest.raises(LaMetricError, match="does not understand"):
        await auth.request_challenge()


@pytest.mark.parametrize(
    ("state", "resolved"),
    [("in-progress", False), ("resolved", True), ("expired", False)],
)
async def test_challenge(
    responses: aioresponses,
    auth: LaMetricLocalAuth,
    state: str,
    resolved: bool,  # noqa: FBT001
) -> None:
    """Test polling a challenge, including the states seen on a real device."""
    data = json.loads(load_fixture("auth_challenge_resolved_sa8.json"))
    data["state"] = state
    responses.get(CHALLENGE_URL, status=200, body=json.dumps(data))

    challenge = await auth.challenge(challenge_id=CHALLENGE_ID)

    assert challenge.state == state
    assert challenge.resolved is resolved


async def test_challenge_unknown(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test the reason of the device is passed on, in its own error shape."""
    responses.get(
        CHALLENGE_URL,
        status=500,
        body='{"error":{ "message":"Failed to get info about challenge"}}',
    )

    with pytest.raises(LaMetricError, match="Failed to get info about challenge"):
        await auth.challenge(challenge_id=CHALLENGE_ID)


async def test_api_key(responses: aioresponses, auth: LaMetricLocalAuth) -> None:
    """Test exchanging a resolved challenge for the API key."""
    responses.post(
        EXCHANGE_URL, status=200, body=load_fixture("auth_exchange_sa8.json")
    )
    responses.get(USERS_URL, status=200, body=load_fixture("auth_users_sa8.json"))

    assert await auth.api_key(challenge_id=CHALLENGE_ID) == "accountintegrationkey"

    exchange = responses.requests[("POST", URL(EXCHANGE_URL))][0]
    assert exchange.kwargs["json"] == {"challenge_id": CHALLENGE_ID}

    # The web interface takes the web admin key from a cookie.
    users = responses.requests[("GET", URL(USERS_URL))][0]
    assert users.kwargs["headers"]["Cookie"] == (
        "no-auth-challenge=1; authorization=webadminkey:"
    )


async def test_api_key_prefers_local(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test a key generated in the LaMetric app wins over the account one."""
    users = json.loads(load_fixture("auth_users_sa8.json"))
    users.append(
        {
            "group": "integration",
            "key": "localkey",
            "name": "",
            "origin": "local",
            "status": "active",
            "uuid": "localuuid",
        }
    )
    responses.post(
        EXCHANGE_URL, status=200, body=load_fixture("auth_exchange_sa8.json")
    )
    responses.get(USERS_URL, status=200, body=json.dumps(users))

    assert await auth.api_key(challenge_id=CHALLENGE_ID) == "localkey"


async def test_api_key_none(responses: aioresponses, auth: LaMetricLocalAuth) -> None:
    """Test a device without any API key yet says what to do."""
    users = [
        user
        for user in json.loads(load_fixture("auth_users_sa8.json"))
        if user["group"] != "integration"
    ]
    responses.post(
        EXCHANGE_URL, status=200, body=load_fixture("auth_exchange_sa8.json")
    )
    responses.get(USERS_URL, status=200, body=json.dumps(users))

    with pytest.raises(LaMetricError, match="generate one in the LaMetric app"):
        await auth.api_key(challenge_id=CHALLENGE_ID)


async def test_api_key_not_resolved(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test exchanging before the button was pressed passes on the reason."""
    responses.post(
        EXCHANGE_URL,
        status=400,
        body='{"error":{ "message":"Invalid challenge status in-progress"}}',
    )

    with pytest.raises(LaMetricError, match="Invalid challenge status in-progress"):
        await auth.api_key(challenge_id=CHALLENGE_ID)


async def test_api_key_no_key_handed_out(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test an exchange without a key raises a LaMetricError."""
    responses.post(EXCHANGE_URL, status=200, body='{"user": {}}')

    with pytest.raises(LaMetricError, match="did not hand out a key"):
        await auth.api_key(challenge_id=CHALLENGE_ID)


async def test_api_key_admin_key_refused(
    responses: aioresponses, auth: LaMetricLocalAuth
) -> None:
    """Test a refused web admin key raises an authentication error."""
    responses.post(
        EXCHANGE_URL, status=200, body=load_fixture("auth_exchange_sa8.json")
    )
    responses.get(USERS_URL, status=401, body='{"error":{ "message":"Invalid auth"}}')

    with pytest.raises(LaMetricAuthenticationError, match="Invalid auth"):
        await auth.api_key(challenge_id=CHALLENGE_ID)


async def test_invalid_json(responses: aioresponses, auth: LaMetricLocalAuth) -> None:
    """Test a broken JSON answer raises a LaMetricError."""
    responses.get(CHALLENGE_URL, status=200, body="{")

    with pytest.raises(LaMetricError, match="invalid JSON"):
        await auth.challenge(challenge_id=CHALLENGE_ID)


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (TimeoutError(), LaMetricConnectionTimeoutError),
        (aiohttp.ClientError(), LaMetricConnectionError),
    ],
)
async def test_connection_errors(
    responses: aioresponses,
    auth: LaMetricLocalAuth,
    exception: Exception,
    expected: type[Exception],
) -> None:
    """Test connection problems raise connection errors, without retrying.

    Requesting a challenge twice would show it twice on the device.
    """
    responses.post(REQUEST_URL, exception=exception, repeat=True)

    with pytest.raises(expected):
        await auth.request_challenge()

    assert len(responses.requests[("POST", URL(REQUEST_URL))]) == 1


async def test_internal_session(responses: aioresponses) -> None:
    """Test the client creates and closes its own session."""
    responses.get(
        CHALLENGE_URL, status=200, body=load_fixture("auth_challenge_resolved_sa8.json")
    )

    async with LaMetricLocalAuth(host="127.0.0.2") as auth:
        challenge = await auth.challenge(challenge_id=CHALLENGE_ID)
        session = auth.session

    assert challenge.resolved is True
    assert session is not None
    assert session.closed


@pytest.mark.parametrize(
    ("status", "supported"),
    [
        # A device from 2022 onward serves its web interface.
        (200, True),
        # An LM 37X8 TIME asks for credentials instead.
        (401, False),
    ],
)
async def test_supported(
    responses: aioresponses,
    auth: LaMetricLocalAuth,
    status: int,
    supported: bool,  # noqa: FBT001
) -> None:
    """Test checking support, without asking the device for a button press."""
    responses.get(f"{WEB_URL}/", status=status, body="")

    assert await auth.supported() is supported
    assert ("POST", URL(REQUEST_URL)) not in responses.requests


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (TimeoutError(), LaMetricConnectionTimeoutError),
        (aiohttp.ClientError(), LaMetricConnectionError),
    ],
)
async def test_supported_connection_errors(
    responses: aioresponses,
    auth: LaMetricLocalAuth,
    exception: Exception,
    expected: type[Exception],
) -> None:
    """Test connection problems while checking support raise connection errors."""
    responses.get(f"{WEB_URL}/", exception=exception)

    with pytest.raises(expected):
        await auth.supported()


async def test_supported_internal_session(responses: aioresponses) -> None:
    """Test checking support creates and closes its own session."""
    responses.get(f"{WEB_URL}/", status=200, body="")

    async with LaMetricLocalAuth(host="127.0.0.2") as auth:
        assert await auth.supported() is True
        session = auth.session

    assert session is not None
    assert session.closed
