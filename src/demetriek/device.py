"""Asynchronous Python client for LaMetric TIME devices."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Any, cast

import aiohttp
import async_timeout
import backoff
from aiohttp import hdrs
from aiohttp.helpers import BasicAuth
from pydantic import parse_obj_as
from yarl import URL

from .const import BrightnessMode
from .exceptions import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
)
from .models import Audio, Bluetooth, Device, Display, Notification, Wifi


@dataclass
class LaMetricDevice:
    """Main class for handling connections with the LaMetric device."""

    host: str
    api_key: str
    request_timeout: float = 8.0
    session: aiohttp.client.ClientSession | None = None

    _close_session: bool = False

    @backoff.on_exception(
        backoff.expo, LaMetricConnectionError, max_tries=3, logger=None
    )
    async def _request(
        self,
        uri: str = "",
        method: str = hdrs.METH_GET,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to a LaMetric device.

        A generic method for sending/handling HTTP requests done gainst
        the LaMetric device.

        Args:
            uri: Request URI, for example `/api/v2/device`.
            method: HTTP method to use for the request.E.g., "GET" or "POST".
            data: Dictionary of data to send to the LaMetric device.

        Returns:
            A Python dictionary (JSON decoded) with the response from the
            LaMetric device.

        Raises:
            LaMetricAuthenticationError: If the API key is invalid.
            LaMetricConnectionError: An error occurred while communication with
                the LaMetric device.
            LaMetricConnectionTimeoutError: A timeout occurred while communicating
                with the LaMetric device.
            LaMetricError: Received an unexpected response from the LaMetric device.
        """
        url = URL.build(scheme="https", host=self.host, port=4343, path=uri)

        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._close_session = True

        try:
            async with async_timeout.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    auth=BasicAuth("dev", self.api_key),
                    headers={"Accept": "application/json"},
                    json=data,
                    raise_for_status=True,
                    ssl=False,
                )

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise LaMetricError(response.status, {"message": await response.text()})
            return await response.json()

        except asyncio.TimeoutError as exception:
            raise LaMetricConnectionTimeoutError(
                f"Timeout occurred while connecting to the LaMetric device at {self.host}"
            ) from exception
        except aiohttp.ClientResponseError as exception:
            if exception.status in [401, 403]:
                raise LaMetricAuthenticationError(
                    f"Authentication to the LaMetric device at {self.host} failed"
                ) from exception
            raise LaMetricError(
                f"Error occurred while connecting to the LaMetric device at {self.host}"
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise LaMetricConnectionError(
                f"Error occurred while communicating with the LaMetric device at {self.host}"
            ) from exception

    async def device(self) -> Device:
        """Get LaMetric device information.

        Returns:
            A Device object, with information about the LaMetric device.
        """
        response = await self._request("/api/v2/device")

        response["wifi"].update(
            mac=response["wifi"].get("address"),
            ssid=response["wifi"].get("essid"),
            rssi=response["wifi"].get("strength"),
        )

        return Device.parse_obj(response)

    async def display(
        self,
        *,
        brightness: int | None = None,
        brightness_mode: BrightnessMode | None = None,
    ) -> Display:
        """Get or set LaMetric device display information.

        Args:
            brightness: Brightness level to set.
            brightness_mode: Brightness mode to set.

        Returns:
            A Display object, with latest or updated information about
            the display of the LaMetric device.
        """
        data: dict[str, int | BrightnessMode] = {}

        if brightness is not None:
            data["brightness"] = brightness

        if brightness_mode is not None:
            data["brightness_mode"] = brightness_mode

        if data:
            response = await self._request(
                "/api/v2/device/display", method=hdrs.METH_PUT, data=data
            )
            return Display.parse_obj(response["success"]["data"])

        response = await self._request("/api/v2/device/display")
        return Display.parse_obj(response)

    async def audio(self, *, volume: int | None = None) -> Audio:
        """Get or set LaMetric device audio information.

        Args:
            volume: Volume level to set.

        Returns:
            An Audio object, with latest or updated information about the
            audio state of the LaMetric device.
        """
        data: dict[str, int] = {}

        if volume is not None:
            data["volume"] = volume

        if data:
            response = await self._request(
                "/api/v2/device/audio", method=hdrs.METH_PUT, data=data
            )
            return Audio.parse_obj(response["success"]["data"])

        data = await self._request("/api/v2/device/audio")
        return Audio.parse_obj(data)

    async def bluetooth(self, *, active: bool | None = None) -> Bluetooth:
        """Get LaMetric device bluetooth information.

        Args:
            active: Whether to activate or deactivate Bluetooth.

        Returns:
            A Bluetooth object, with the latest or updated Bluetooth information.
        """
        data: dict[str, int] = {}

        if active is not None:
            data["active"] = active

        if data:
            response = await self._request(
                "/api/v2/device/bluetooth", method=hdrs.METH_PUT, data=data
            )
            response = response["success"]["data"]
        else:
            response = await self._request("/api/v2/device/bluetooth")
        response.update(address=response.get("mac"))
        return Bluetooth.parse_obj(response)

    async def wifi(self) -> Wifi:
        """Get LaMetric device bluetooth information.

        Returns:
            A Wifi object with the latest Wi-Fi state of the device.
        """
        data = await self._request("/api/v2/device/wifi")
        data.update(ip=data.get("ipv4"), rssi=data.get("signal_strength"))
        return Wifi.parse_obj(data)

    async def app_next(self) -> None:
        """Switch to the next app on LaMetric Time.

        App order is controlled by the user via LaMetric Time app.
        """
        await self._request("/api/v2/device/apps/next", method=hdrs.METH_PUT)

    async def app_previous(self) -> None:
        """Switch to the next app on LaMetric Time.

        App order is controlled by the user via LaMetric Time app.
        """
        await self._request("/api/v2/device/apps/prev", method=hdrs.METH_PUT)

    async def notify(
        self,
        *,
        notification: Notification,
    ) -> int:
        """Send a notification to a LaMetric device.

        Args:
            notification: A Notification object.

        Returns:
            The ID of the notification.
        """
        response = await self._request(
            "/api/v2/device/notifications",
            method=hdrs.METH_POST,
            data=notification.dict(
                by_alias=True,
                exclude_none=True,
            ),
        )
        return cast(int, response["success"]["id"])

    async def dismiss_notification(self, *, notification_id: int) -> None:
        """Remove a notification from the queue.

        In case if it is already visible - dismisses it.

        Args:
            notification_id: Notification ID to dismiss.
        """
        await self._request(
            f"/api/v2/device/notifications/{notification_id}",
            method=hdrs.METH_DELETE,
        )

    async def notification_queue(self) -> list[Notification]:
        """Get the list of all notifications in the queue.

        Notifications with higher priority will be first in the list.

        Returns:
            A list of Notification objects.
        """
        data = await self._request("/api/v2/device/notifications")
        return parse_obj_as(list[Notification], data)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> LaMetricDevice:
        """Async enter.

        Returns:
            The LaMetricDevice object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
