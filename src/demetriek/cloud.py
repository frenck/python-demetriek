"""Asynchronous Python client for LaMetric TIME devices."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Any

import aiohttp
import async_timeout
import backoff
from aiohttp import hdrs
from pydantic import parse_obj_as
from yarl import URL

from .exceptions import (
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

    @backoff.on_exception(
        backoff.expo, LaMetricConnectionError, max_tries=3, logger=None
    )
    async def _request(
        self,
        uri: str = "",
    ) -> Any:
        """Handle a request to the  LaMetric cloud.

        A generic method for sending/handling HTTP requests done gainst
        the LaMetric cloud.

        Args:
            uri: Request URI, for example `/api/v2/users/me`.

        Returns:
            A Python dictionary (JSON decoded) with the response from the
            LaMetric device.

        Raises:
            LaMetricConnectionError: An error occurred while communication with
                the LaMetric device.
            LaMetricConnectionTimeoutError: A timeout occurred while communicating
                with the LaMetric device.
            LaMetricError: Received an unexpected response from the LaMetric device.
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
            async with async_timeout.timeout(self.request_timeout):
                response = await self.session.request(
                    hdrs.METH_GET,
                    url,
                    headers=headers,
                    raise_for_status=True,
                )

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise LaMetricError(response.status, {"message": await response.text()})
            return await response.json()

        except asyncio.TimeoutError as exception:
            raise LaMetricConnectionTimeoutError(
                "Timeout occurred while connecting to the LaMetric cloud"
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise LaMetricConnectionError(
                "Error occurred while communicating with the LaMetric cloud"
            ) from exception

    async def current_user(self) -> User:
        """Get LaMetric user information.

        Returns:
            A User object, with information about the current user.
        """
        response = await self._request("/api/v2/me")
        return User.parse_obj(response)

    async def devices(self) -> list[CloudDevice]:
        """Get LaMetric devices from the cloud.

        Returns:
            A list of CloudDevices.
        """
        response = await self._request("/api/v2/users/me/devices")
        return parse_obj_as(list[CloudDevice], response)

    async def device(self, device_id: int) -> CloudDevice:
        """Get a LaMetric device from the cloud.

        Args:
            device_id: The ID of the device to get information for.

        Returns:
            A CloudDevice object, with information about the request device.
        """
        response = await self._request(f"/api/v2/users/me/devices/{device_id}")
        return CloudDevice.parse_obj(response)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> LaMetricCloud:
        """Async enter.

        Returns:
            The LaMetricCloud object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
