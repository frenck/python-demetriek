"""Exceptions for LaMetric."""
from __future__ import annotations

from typing import Any

import aiohttp


class LaMetricError(Exception):
    """Generic LaMetric exception."""


class LaMetricConnectionError(LaMetricError):
    """LaMetric connection exception."""


class LaMetricAuthenticationError(LaMetricError):
    """LaMetric authentication exception."""


class LaMetricConnectionTimeoutError(LaMetricConnectionError):
    """LaMetric connection Timeout exception."""


def raise_on_data_error(
    host: str, data: dict[str, Any], raising_exception: aiohttp.ClientResponseError
) -> None:
    """Raise an exception (if appropriate) based on response data.

    Args:
        host: The IP address/hostname of the LaMetric device.
        data: An API response payload.
        raising_exception: The original aiohttp.ClientResponseError.

    Raises:
        LaMetricAuthenticationError: If the API key is invalid.
        LaMetricError: If the response data contains an error message.
    """
    if (errors := data.get("errors")) is None:
        return

    # Although this exception doesn't make use of the response data, we include it here
    # for completeness and specificity:
    if raising_exception.status in (401, 403):
        raise LaMetricAuthenticationError(
            f"Authentication to the LaMetric device at {host} failed"
        ) from raising_exception

    raise LaMetricError(
        (
            f"Error occurred while communicating with the LaMetric device at {host}: "
            f"{errors[0]['message']}"
        )
    ) from raising_exception
