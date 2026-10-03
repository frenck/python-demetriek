"""Asynchronous Python client for LaMetric TIME devices."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Self

import aiohttp
from aiohttp import hdrs
from mashumaro.exceptions import MissingField
from yarl import URL

from .exceptions import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
    error_message,
)
from .models import AuthChallenge


@dataclass
class LaMetricLocalAuth:
    """Get the API key of a LaMetric device, with a press on its button.

    This talks to the web interface of the device, which LaMetric does not
    document. Devices from 2022 onward have it, an LM 37X8 TIME does not.

    Request a challenge, have someone press the button on top of the device
    while it shows it, and exchange the resolved challenge for the API key.
    No LaMetric account or cloud is involved.
    """

    host: str
    request_timeout: float = 8.0
    session: aiohttp.client.ClientSession | None = None

    _close_session: bool = False

    async def _request(
        self,
        uri: str,
        *,
        method: str = hdrs.METH_GET,
        query: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        admin_key: str | None = None,
    ) -> Any:
        """Handle a request to the web interface of a LaMetric device.

        Args:
        ----
            uri: Request URI, for example `/api/v1/user`.
            method: HTTP method to use for the request.
            query: Query parameters to add to the URI.
            data: Dictionary of data to send to the device.
            admin_key: The web admin key, for requests that need it.

        Returns:
        -------
            A Python dictionary (JSON decoded) with the response.

        Raises:
        ------
            LaMetricAuthenticationError: The web admin key was not accepted.
            LaMetricConnectionError: An error occurred while communicating with
                the LaMetric device.
            LaMetricConnectionTimeoutError: A timeout occurred while communicating
                with the LaMetric device.
            LaMetricError: Received an unexpected response from the device.

        """
        url = URL.build(scheme="https", host=self.host, path=uri, query=query or {})

        headers = {"Accept": "application/json"}
        if admin_key is not None:
            # The web interface takes the key from a cookie, not from basic auth.
            headers["Cookie"] = f"no-auth-challenge=1; authorization={admin_key}:"

        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._close_session = True

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    ssl=False,
                )
                body = await response.text()

            if response.status >= HTTPStatus.BAD_REQUEST:
                reason = error_message(body) or response.reason
                if response.status == HTTPStatus.UNAUTHORIZED:
                    msg = (
                        f"Authentication to the LaMetric device at {self.host}"
                        f" failed: {reason}"
                    )
                    raise LaMetricAuthenticationError(msg)
                msg = (
                    f"The LaMetric device at {self.host} returned an error"
                    f" ({response.status}): {reason}"
                )
                raise LaMetricError(msg)

            try:
                return await response.json(content_type=None)
            except ValueError as exception:
                msg = f"The LaMetric device at {self.host} answered with invalid JSON"
                raise LaMetricError(msg) from exception

        except TimeoutError as exception:
            msg = (
                "Timeout occurred while connecting to the LaMetric device"
                f" at {self.host}"
            )
            raise LaMetricConnectionTimeoutError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = (
                "Error occurred while communicating with the LaMetric device"
                f" at {self.host}"
            )
            raise LaMetricConnectionError(msg) from exception

    def _parse_challenge(self, data: Any) -> AuthChallenge:
        """Parse a challenge answered by the device.

        Args:
        ----
            data: The JSON decoded challenge.

        Returns:
        -------
            The challenge.

        Raises:
        ------
            LaMetricError: The challenge does not look like one.

        """
        try:
            return AuthChallenge.from_dict(data)
        except (MissingField, ValueError) as exception:
            msg = (
                f"The LaMetric device at {self.host} answered with data this"
                f" library does not understand: {exception}"
            )
            raise LaMetricError(msg) from exception

    async def request_challenge(self) -> AuthChallenge:
        """Ask the device to have its button pressed.

        The device shows the challenge on its screen, someone then has
        `duration` seconds to press the button on top of the device.

        Returns
        -------
            The challenge, to poll with `challenge()`.

        Raises
        ------
            LaMetricError: The device does not support this, for example an
                LM 37X8 TIME.

        """
        try:
            response = await self._request(
                "/api/v1/user/request",
                method=hdrs.METH_POST,
                query={"group": "web_admin"},
            )
        except LaMetricAuthenticationError as exception:
            # A device without this flow asks for credentials instead.
            msg = (
                f"The LaMetric device at {self.host} does not support getting"
                " its API key with a press on its button"
            )
            raise LaMetricError(msg) from exception

        challenge = response.get("challenge") if isinstance(response, dict) else None
        return self._parse_challenge(challenge)

    async def challenge(self, *, challenge_id: str) -> AuthChallenge:
        """Get the current state of a challenge.

        Args:
        ----
            challenge_id: ID of the challenge, from `request_challenge()`.

        Returns:
        -------
            The challenge, which is resolved once the button was pressed.

        """
        response = await self._request(f"/api/v1/user/challenge/{challenge_id}")
        return self._parse_challenge(response)

    async def api_key(self, *, challenge_id: str) -> str:
        """Exchange a resolved challenge for the API key of the device.

        Args:
        ----
            challenge_id: ID of the resolved challenge.

        Returns:
        -------
            The API key, to use with `LaMetricDevice`.

        Raises:
        ------
            LaMetricError: The challenge is not resolved, or the device has
                no API key.

        """
        response = await self._request(
            "/api/v1/user/request/exchange",
            method=hdrs.METH_POST,
            data={"challenge_id": challenge_id},
        )

        try:
            admin_key = response["user"]["key"]
        except (KeyError, TypeError) as exception:
            msg = f"The LaMetric device at {self.host} did not hand out a key"
            raise LaMetricError(msg) from exception

        # The exchange hands out a web admin key, which stays the same when
        # the API key is regenerated. The API key itself is in the users.
        users = await self._request("/api/v1/user", admin_key=admin_key)
        keys = [
            user
            for user in (users if isinstance(users, list) else [])
            if isinstance(user, dict)
            and user.get("group") == "integration"
            and user.get("status") == "active"
            and isinstance(user.get("key"), str)
        ]
        if not keys:
            msg = (
                f"The LaMetric device at {self.host} has no API key yet,"
                " generate one in the LaMetric app first"
            )
            raise LaMetricError(msg)

        # A key generated in the LaMetric app stays on the device, the one
        # for the LaMetric account comes from the cloud. Prefer the local one.
        keys.sort(key=lambda user: user.get("origin") != "local")
        return keys[0]["key"]

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The LaMetricLocalAuth object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
