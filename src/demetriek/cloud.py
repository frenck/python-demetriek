"""Asynchronous Python client for LaMetric TIME devices."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Any, Self

import aiohttp
from aiohttp import hdrs
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from yarl import URL

from .exceptions import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
)
from .models import CloudDevice, User


@dataclass
class LaMetricCloud:
    """Main class for handling connections with the LaMetric cloud."""

    token: str
    request_timeout: float = 8.0
    session: aiohttp.client.ClientSession | None = None

    _close_session: bool = False

    @retry(
        retry=retry_if_exception_type(LaMetricConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(),
        reraise=True,
    )
    async def _request(
        self,
        uri: str = "",
    ) -> Any:
        """Handle a request to the LaMetric cloud.

        A generic method for sending/handling HTTP requests done against
        the LaMetric cloud.

        Args:
        ----
            uri: Request URI, for example `/api/v2/users/me`.

        Returns:
        -------
            A Python dictionary (JSON decoded) with the response from the
            LaMetric cloud.

        Raises:
        ------
            LaMetricAuthenticationError: If the token is invalid or expired.
            LaMetricConnectionError: An error occurred while communicating with
                the LaMetric cloud.
            LaMetricConnectionTimeoutError: A timeout occurred while communicating
                with the LaMetric cloud.
            LaMetricError: Received an unexpected response from the LaMetric cloud.

        """
        url = URL.build(scheme="https", host="developer.lametric.com", path=uri)

        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._close_session = True

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    hdrs.METH_GET,
                    url,
                    headers=headers,
                    raise_for_status=True,
                )

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise LaMetricError(
                    response.status,
                    {"message": await response.text()},
                )
            return await response.json()

        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to the LaMetric cloud"
            raise LaMetricConnectionTimeoutError(msg) from exception
        except aiohttp.ClientResponseError as exception:
            # The cloud did answer, so this is not a connection problem and
            # retrying will not help. An expired token must surface as an
            # authentication error, so the caller can ask for a new one.
            if exception.status in [401, 403]:
                msg = "Authentication to the LaMetric cloud failed"
                raise LaMetricAuthenticationError(msg) from exception
            msg = "Error occurred while connecting to the LaMetric cloud"
            raise LaMetricError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the LaMetric cloud"
            raise LaMetricConnectionError(msg) from exception

    async def current_user(self) -> User:
        """Get LaMetric user information.

        Returns
        -------
            A User object, with information about the current user.

        """
        response = await self._request("/api/v2/users/me")
        return User.from_dict(response)

    async def devices(self) -> list[CloudDevice]:
        """Get LaMetric devices from the cloud.

        Returns
        -------
            A list of CloudDevices.

        """
        response = await self._request("/api/v2/users/me/devices")
        return [CloudDevice.from_dict(cloud_device) for cloud_device in response]

    async def device(self, device_id: int) -> CloudDevice:
        """Get a LaMetric device from the cloud.

        Args:
        ----
            device_id: The ID of the device to get information for.

        Returns:
        -------
            A CloudDevice object, with information about the request device.

        """
        response = await self._request(f"/api/v2/users/me/devices/{device_id}")
        return CloudDevice.from_dict(response)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The LaMetricCloud object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
