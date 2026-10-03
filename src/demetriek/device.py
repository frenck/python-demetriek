"""Asynchronous Python client for LaMetric TIME devices."""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Self, TypeVar

import aiohttp
from aiohttp import hdrs
from aiohttp.helpers import BasicAuth
from mashumaro.exceptions import MissingField
from mashumaro.mixins.orjson import DataClassORJSONMixin
from tenacity import (
    RetryCallState,
    retry,
    stop_after_attempt,
    wait_exponential,
)
from yarl import URL

from .const import (
    TRANSIENT_HTTP_STATUSES,
    ScreensaverMode,
    StreamFillType,
    StreamRenderMode,
)
from .exceptions import (
    LaMetricAuthenticationError,
    LaMetricConnectionError,
    LaMetricConnectionTimeoutError,
    LaMetricError,
    error_message,
)
from .models import (
    API,
    App,
    Audio,
    Bluetooth,
    Chart,
    Device,
    Display,
    Goal,
    Notification,
    Simple,
    Stream,
    StreamFadingPixels,
    StreamSession,
    Wifi,
)

if TYPE_CHECKING:
    from datetime import time

    from .const import BrightnessMode, DeviceMode

_LOGGER = logging.getLogger(__package__)

_ModelT = TypeVar("_ModelT", bound=DataClassORJSONMixin)


def _can_retry(retry_state: RetryCallState) -> bool:
    """Tell whether a failed request to the device is safe to repeat.

    Reading is always safe to repeat. A request that changes the device is
    only repeated when it never reached the device. Otherwise a slow answer
    could show the same notification twice, or skip past an app.
    """
    if retry_state.outcome is None:
        return False

    exception = retry_state.outcome.exception()
    if not isinstance(exception, LaMetricConnectionError):
        return False

    # The method is keyword only on _request, so it always ends up here.
    if retry_state.kwargs.get("method", hdrs.METH_GET) == hdrs.METH_GET:
        return True

    return isinstance(
        exception.__cause__,
        (aiohttp.ClientConnectorError, aiohttp.ConnectionTimeoutError, socket.gaierror),
    )


@dataclass
class LaMetricDevice:
    """Main class for handling connections with the LaMetric device."""

    host: str
    api_key: str = field(repr=False)
    request_timeout: float = 8.0
    session: aiohttp.client.ClientSession | None = None

    _close_session: bool = False

    @retry(
        retry=_can_retry,
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
        """Handle a request to a LaMetric device.

        A generic method for sending/handling HTTP requests done against
        the LaMetric device.

        Args:
        ----
            uri: Request URI, for example `/api/v2/device`.
            method: HTTP method to use for the request, for example "GET" or "POST".
            data: Dictionary of data to send to the LaMetric device.

        Returns:
        -------
            A Python dictionary (JSON decoded) with the response from the
            LaMetric device.

        Raises:
        ------
            LaMetricAuthenticationError: If the API key is invalid.
            LaMetricConnectionError: An error occurred while communicating with
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
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    auth=BasicAuth("dev", self.api_key),
                    headers={"Accept": "application/json"},
                    json=data,
                    ssl=False,
                )
                body = await response.text()

            # The device did answer, so this is not a connection problem and
            # retrying will not help. Pass on what the device says is wrong.
            # Unless it says it is briefly unable to answer at all.
            if response.status >= HTTPStatus.BAD_REQUEST:
                reason = error_message(body) or response.reason
                if response.status in TRANSIENT_HTTP_STATUSES:
                    msg = (
                        f"The LaMetric device at {self.host} is temporarily"
                        f" unavailable ({response.status}): {reason}"
                    )
                    raise LaMetricConnectionError(msg)
                if response.status in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]:
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

            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                msg = (
                    f"The LaMetric device at {self.host} answered with"
                    f" {content_type!r}, instead of JSON"
                )
                raise LaMetricError(msg)

            try:
                return await response.json()
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

    def _parse(self, model: type[_ModelT], data: Any) -> _ModelT:
        """Parse a response of the LaMetric device into a model.

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
                because a firmware update changed it.

        """
        try:
            return model.from_dict(data)
        except (MissingField, ValueError) as exception:
            msg = (
                f"The LaMetric device at {self.host} answered with data this"
                f" library does not understand: {exception}"
            )
            raise LaMetricError(msg) from exception

    async def api(self) -> API:
        """Get the API version and the endpoints the device supports.

        Returns
        -------
            An API object, with the API version and a map of endpoints.

        """
        response = await self._request("/api/v2")
        return self._parse(API, response)

    async def device(self) -> Device:
        """Get LaMetric device information.

        Returns
        -------
            A Device object, with information about the LaMetric device.

        """
        response = await self._request("/api/v2/device")

        # Leave a missing Wi-Fi block to the parsing below, which reports it.
        if isinstance(wifi := response.get("wifi"), dict):
            wifi.update(
                mac=wifi.get("address", wifi.get("mac")),
                ssid=wifi.get("essid", wifi.get("ssid")),
                rssi=wifi.get("strength", wifi.get("rssi")),
            )

        return self._parse(Device, response)

    async def set_device_mode(self, *, mode: DeviceMode) -> None:
        """Set the mode of the LaMetric device.

        The device only echoes back the mode it applied, so nothing is
        returned. Call `device()` to read the resulting state.

        Args:
        ----
            mode: Mode to set the device to.

        """
        await self._request(
            "/api/v2/device",
            method=hdrs.METH_PUT,
            data={"mode": mode},
        )

    # Keyword-only setters for each display property the device accepts.
    async def display(  # noqa: PLR0913 # pylint: disable=too-many-arguments
        self,
        *,
        brightness: int | None = None,
        brightness_mode: BrightnessMode | None = None,
        screensaver_enabled: bool | None = None,
        screensaver_mode: ScreensaverMode | None = None,
        screensaver_mode_enabled: bool | None = None,
        screensaver_start_time: time | None = None,
        screensaver_end_time: time | None = None,
        on: bool | None = None,
    ) -> Display:
        """Get or set LaMetric device display information.

        The device keeps a single screensaver mode active; enabling one mode
        disables the other. `screensaver_enabled` is the separate master
        switch and can be set without touching the modes.

        Args:
        ----
            brightness: Brightness level to set.
            brightness_mode: Brightness mode to set.
            screensaver_enabled: Whether the screensaver should be enabled.
            screensaver_mode: Screensaver mode to configure. Only pick a mode
                the device reports in `screensaver.modes`. A TIME accepts
                screen_off, but only switches its other modes off, leaving
                the screensaver without any mode at all.
            screensaver_mode_enabled: Whether to enable the screensaver mode.
            screensaver_start_time: Time in GMT the screensaver starts,
                for the time based mode.
            screensaver_end_time: Time in GMT the screensaver ends,
                for the time based mode.
            on: Whether the display should be turned on or off.

        Returns:
        -------
            A Display object, with latest or updated information about
            the display of the LaMetric device.

        Raises:
        ------
            ValueError: The time based mode was given without both of
                its times.

        """
        # The device wants both times on every time based write, even one
        # that only toggles the mode. It rejects a lone end time and
        # quietly ignores a lone start time, so catch that here rather
        # than let it look like it worked.
        if screensaver_mode is ScreensaverMode.TIME_BASED and (
            screensaver_start_time is None or screensaver_end_time is None
        ):
            msg = (
                "The time based screensaver mode needs both"
                " screensaver_start_time and screensaver_end_time"
            )
            raise ValueError(msg)

        data: dict[str, Any] = {}

        if brightness is not None:
            data["brightness"] = brightness

        if brightness_mode is not None:
            data["brightness_mode"] = brightness_mode

        screensaver: dict[str, Any] = {}

        if screensaver_enabled is not None:
            screensaver["enabled"] = screensaver_enabled

        if screensaver_mode is not None:
            mode_params: dict[str, Any] = {}

            if screensaver_mode_enabled is not None:
                mode_params["enabled"] = screensaver_mode_enabled

            if screensaver_start_time is not None:
                mode_params["start_time"] = screensaver_start_time.isoformat()

            if screensaver_end_time is not None:
                mode_params["end_time"] = screensaver_end_time.isoformat()

            screensaver["mode"] = screensaver_mode
            if mode_params:
                screensaver["mode_params"] = mode_params

        if screensaver:
            data["screensaver"] = screensaver

        if on is not None:
            data["on"] = on

        if data:
            response = await self._request(
                "/api/v2/device/display",
                method=hdrs.METH_PUT,
                data=data,
            )
            return self._parse(Display, response["success"]["data"])

        response = await self._request("/api/v2/device/display")
        return self._parse(Display, response)

    async def audio(self, *, volume: int | None = None) -> Audio:
        """Get or set LaMetric device audio information.

        Args:
        ----
            volume: Volume level to set.

        Returns:
        -------
            An Audio object, with latest or updated information about the
            audio state of the LaMetric device.

        """
        data: dict[str, int] = {}

        if volume is not None:
            data["volume"] = volume

        if data:
            response = await self._request(
                "/api/v2/device/audio",
                method=hdrs.METH_PUT,
                data=data,
            )
            return self._parse(Audio, response["success"]["data"])

        data = await self._request("/api/v2/device/audio")
        return self._parse(Audio, data)

    async def bluetooth(
        self,
        *,
        active: bool | None = None,
        name: str | None = None,
    ) -> Bluetooth:
        """Get or set the LaMetric device Bluetooth information.

        Args:
        ----
            active: Whether to activate or deactivate Bluetooth.
            name: New Bluetooth name of the device.

        Returns:
        -------
            A Bluetooth object, with the latest or updated Bluetooth information.

        """
        data: dict[str, bool | str] = {}

        if active is not None:
            data["active"] = active

        if name is not None:
            data["name"] = name

        if data:
            response = await self._request(
                "/api/v2/device/bluetooth",
                method=hdrs.METH_PUT,
                data=data,
            )
            response = response["success"]["data"]
        else:
            response = await self._request("/api/v2/device/bluetooth")
        # The Bluetooth endpoint calls the address "mac", the device endpoint
        # calls it "address". Only fill it in when the device left it out.
        response.setdefault("address", response.get("mac"))
        return self._parse(Bluetooth, response)

    async def wifi(self) -> Wifi:
        """Get LaMetric device Wi-Fi information.

        Returns
        -------
            A Wifi object with the latest Wi-Fi state of the device.

        """
        data = await self._request("/api/v2/device/wifi")
        # The Wi-Fi endpoint uses other names than the device endpoint does.
        # Only fill them in when the device left them out.
        data.setdefault("ip", data.get("ipv4"))
        data.setdefault("rssi", data.get("signal_strength"))
        return self._parse(Wifi, data)

    async def apps(self) -> dict[str, App]:
        """Get the apps installed on LaMetric Time.

        Returns
        -------
            The installed apps, keyed by package name.

        """
        response = await self._request("/api/v2/device/apps")
        return {package: self._parse(App, app) for package, app in response.items()}

    async def app(self, *, package: str) -> App:
        """Get a single app installed on LaMetric Time.

        Widgets are reported without their visibility here; use `apps()`
        to see which widget is visible.

        Args:
        ----
            package: Package name of the app, for example
                `com.lametric.clock`.

        Returns:
        -------
            An App object.

        """
        response = await self._request(f"/api/v2/device/apps/{package}")
        return self._parse(App, response)

    async def activate_widget(self, *, package: str, widget_id: str) -> None:
        """Show a specific widget of an app on LaMetric Time.

        Args:
        ----
            package: Package name of the app the widget belongs to.
            widget_id: ID of the widget to show.

        """
        await self._request(
            f"/api/v2/device/apps/{package}/widgets/{widget_id}/activate",
            method=hdrs.METH_PUT,
        )

    async def app_action(  # pylint: disable=too-many-arguments
        self,
        *,
        package: str,
        widget_id: str,
        action: str,
        params: dict[str, Any] | None = None,
        activate: bool | None = None,
    ) -> dict[str, Any]:
        """Run an action of an app on LaMetric Time.

        The actions an app offers, and the parameters they take, are
        reported by `apps()` and `app()`.

        Args:
        ----
            package: Package name of the app the widget belongs to.
            widget_id: ID of the widget to run the action on.
            action: Name of the action, for example `clock.alarm`.
            params: Parameters for the action.
            activate: Whether to show the widget when running the action.

        Returns:
        -------
            The data the app returned for the action, which is often empty.

        """
        data: dict[str, Any] = {"id": action}

        if params is not None:
            data["params"] = params

        if activate is not None:
            data["activate"] = activate

        response = await self._request(
            f"/api/v2/device/apps/{package}/widgets/{widget_id}/actions",
            method=hdrs.METH_POST,
            data=data,
        )
        return response.get("success", {}).get("data", {})

    async def update_widget(
        self,
        *,
        package: str,
        widget_id: str,
        frames: list[Chart | Goal | Simple],
    ) -> None:
        """Push new frames to a widget, for example one of the My Data DIY app.

        The widget keeps showing these frames until the next update. The
        device accepts any widget ID without complaint, so take it from
        `apps()` or `app()` rather than guessing.

        Args:
        ----
            package: Package name of the app the widget belongs to, for
                example `com.lametric.diy.devwidget`.
            widget_id: ID of the widget to update.
            frames: The frames to show, in order.

        """
        await self._request(
            f"/api/v2/widget/update/{package}/{widget_id}",
            method=hdrs.METH_POST,
            data={"frames": [frame.to_dict() for frame in frames]},
        )

    async def app_next(self) -> None:
        """Switch to the next app on LaMetric Time.

        App order is controlled by the user via LaMetric Time app.
        """
        await self._request("/api/v2/device/apps/next", method=hdrs.METH_PUT)

    async def app_previous(self) -> None:
        """Switch to the previous app on LaMetric Time.

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
        ----
            notification: A Notification object.

        Returns:
        -------
            The ID of the notification.

        """
        response = await self._request(
            "/api/v2/device/notifications",
            method=hdrs.METH_POST,
            data=notification.to_dict(),
        )
        return int(response["success"]["id"])

    async def dismiss_notification(self, *, notification_id: int) -> None:
        """Remove a notification from the queue.

        In case if it is already visible - dismisses it.

        Args:
        ----
            notification_id: Notification ID to dismiss.

        """
        await self._request(
            f"/api/v2/device/notifications/{notification_id}",
            method=hdrs.METH_DELETE,
        )

    async def dismiss_all_notifications(self) -> None:
        """Dismiss all notifications in the queue."""
        # Only the IDs are needed here, so skip parsing the notifications.
        # A notification this library cannot parse must still be dismissed.
        notifications = await self._request("/api/v2/device/notifications")

        # Dismiss notifications in reverse order to avoid them showing up
        # during rapid dismissal.
        for notification in reversed(notifications):
            if notification_id := notification.get("id"):
                await self.dismiss_notification(notification_id=int(notification_id))

    async def dismiss_current_notification(self) -> None:
        """Dismiss current notification."""
        # Only the ID is needed here, so skip parsing the notification.
        # A notification this library cannot parse must still be dismissed.
        notification = await self._request("/api/v2/device/notifications/current")

        if notification and (notification_id := notification.get("id")):
            await self.dismiss_notification(notification_id=int(notification_id))

    async def notification(self, *, notification_id: int) -> Notification:
        """Get a single notification from the queue.

        Args:
        ----
            notification_id: Notification ID to get.

        Returns:
        -------
            A Notification object.

        """
        response = await self._request(
            f"/api/v2/device/notifications/{notification_id}",
        )
        return self._parse(Notification, response)

    async def notification_current(self) -> Notification | None:
        """Get the current notification.

        Returns
        -------
            A Notification object, or None when no notification is
            currently on display.

        """
        if data := await self._request("/api/v2/device/notifications/current"):
            return self._parse(Notification, data)
        return None

    async def notification_queue(self) -> list[Notification]:
        """Get the list of all notifications in the queue.

        Notifications with higher priority will be first in the list.
        Notifications this library cannot parse, for example ones with a frame
        type it does not know yet, are logged and left out.

        Returns
        -------
            A list of Notification objects.

        """
        data = await self._request("/api/v2/device/notifications")

        notifications: list[Notification] = []
        for notification in data:
            try:
                notifications.append(self._parse(Notification, notification))
            except LaMetricError:
                notification_id = (
                    notification.get("id") if isinstance(notification, dict) else None
                )
                _LOGGER.warning(
                    "Skipping notification %s, its format is not supported",
                    notification_id,
                )
        return notifications

    async def stream(self) -> Stream:
        """Get the stream state and canvas size of the device.

        Streaming is not available on every device. An LM 37X8 TIME on
        firmware 2.3.9 (API 2.3.0) does not have it and answers with a 404,
        an sa8 TIME on firmware 3.2.6 (API 2.4.0) does. `api()` lists the
        stream endpoints when the device has them.

        Returns
        -------
            A Stream object, with the stream state and the canvas sizes.

        """
        response = await self._request("/api/v2/device/stream")
        return self._parse(Stream, response)

    async def stream_start(
        self,
        *,
        fill_type: StreamFillType = StreamFillType.SCALE,
        render_mode: StreamRenderMode = StreamRenderMode.PIXEL,
        fading_pixels: StreamFadingPixels | None = None,
    ) -> StreamSession:
        """Start a stream, so the device accepts LMSP frames over UDP.

        Args:
        ----
            fill_type: How to fill a screen that is larger than the canvas.
            render_mode: Whether frames map onto square or triangular pixels.
            fading_pixels: Settings for the fading pixels effect, which is
                only applied when given.

        Returns:
        -------
            A StreamSession object, with the session ID and the UDP port to
            send frames to.

        """
        post_process: dict[str, Any] = {"type": "none"}
        if fading_pixels is not None:
            post_process = {
                "type": "effect",
                "params": {
                    "effect_type": "fading_pixels",
                    "effect_params": fading_pixels.to_dict(),
                },
            }

        response = await self._request(
            "/api/v2/device/stream/start",
            method=hdrs.METH_PUT,
            data={
                "canvas": {
                    "fill_type": fill_type,
                    "render_mode": render_mode,
                    "post_process": post_process,
                }
            },
        )

        # The canvas settings come back nested, flatten them into the session.
        data = response["success"]["data"]
        return self._parse(StreamSession, {**data.pop("canvas"), **data})

    async def stream_stop(self) -> None:
        """Stop the stream, so the device returns to normal operation."""
        await self._request("/api/v2/device/stream/stop", method=hdrs.METH_PUT)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The LaMetricDevice object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
