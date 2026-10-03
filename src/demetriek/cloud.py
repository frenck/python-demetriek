"""Asynchronous Python client for LaMetric TIME devices."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Self, TypeVar

import aiohttp
from aiohttp import hdrs
from mashumaro.exceptions import MissingField
from mashumaro.mixins.orjson import DataClassORJSONMixin
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from yarl import URL

from .const import TRANSIENT_HTTP_STATUSES
from .exceptions import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
    error_message,
)
from .models import CloudDevice, User

_ModelT = TypeVar("_ModelT", bound=DataClassORJSONMixin)


@dataclass
class LaMetricCloud:
    """Main class for handling connections with the LaMetric cloud."""

    token: str = field(repr=False)
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
        *,
        method: str = hdrs.METH_GET,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to the LaMetric cloud.

        A generic method for sending/handling HTTP requests done against
        the LaMetric cloud.

        Args:
        ----
            uri: Request URI, for example `/api/v2/users/me`.
            method: HTTP method to use for the request, for example "GET" or "PUT".
            data: Dictionary of data to send to the LaMetric cloud.

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
                    method,
                    url,
                    headers=headers,
                    json=data,
                )
                body = await response.text()

            # The cloud did answer, so this is not a connection problem and
            # retrying will not help, unless it says it is briefly unable to
            # answer at all. An expired token must surface as an
            # authentication error, so the caller can ask for a new one.
            if response.status >= HTTPStatus.BAD_REQUEST:
                reason = error_message(body) or response.reason
                if response.status in TRANSIENT_HTTP_STATUSES:
                    msg = (
                        "The LaMetric cloud is temporarily unavailable"
                        f" ({response.status}): {reason}"
                    )
                    raise LaMetricConnectionError(msg)
                if response.status in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]:
                    msg = f"Authentication to the LaMetric cloud failed: {reason}"
                    raise LaMetricAuthenticationError(msg)
                msg = (
                    f"The LaMetric cloud returned an error ({response.status}):"
                    f" {reason}"
                )
                raise LaMetricError(msg)

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                msg = (
                    f"The LaMetric cloud answered with {content_type!r},"
                    " instead of JSON"
                )
                raise LaMetricError(msg)

            try:
                return await response.json()
            except ValueError as exception:
                msg = "The LaMetric cloud answered with invalid JSON"
                raise LaMetricError(msg) from exception

        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to the LaMetric cloud"
            raise LaMetricConnectionTimeoutError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the LaMetric cloud"
            raise LaMetricConnectionError(msg) from exception

    def _parse(self, model: type[_ModelT], data: Any) -> _ModelT:
        """Parse a response of the LaMetric cloud into a model.

        Args:
        ----
            model: The model to parse the response into.
            data: The JSON decoded response.

        Returns:
        -------
            The model, filled with the response.

        Raises:
        ------
            LaMetricError: The response does not fit the model, for example
                because the cloud API changed.

        """
        try:
            return model.from_dict(data)
        except (MissingField, ValueError) as exception:
            msg = (
                "The LaMetric cloud answered with data this library does not"
                f" understand: {exception}"
            )
            raise LaMetricError(msg) from exception

    async def current_user(self) -> User:
        """Get LaMetric user information.

        Returns
        -------
            A User object, with information about the current user.

        """
        response = await self._request("/api/v2/users/me")
        return self._parse(User, response)

    async def devices(self) -> list[CloudDevice]:
        """Get LaMetric devices from the cloud.

        Returns
        -------
            A list of CloudDevices.

        """
        response = await self._request("/api/v2/users/me/devices")
        return [self._parse(CloudDevice, cloud_device) for cloud_device in response]

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
        return self._parse(CloudDevice, response)

    async def rename_device(self, device_id: int, *, name: str) -> None:
        """Rename a LaMetric device in the cloud.

        This needs a token with the `devices_write` scope.

        Args:
        ----
            device_id: The ID of the device to rename.
            name: The new name of the device.

        """
        await self._request(
            f"/api/v2/users/me/devices/{device_id}",
            method=hdrs.METH_PUT,
            data={"name": name},
        )

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
