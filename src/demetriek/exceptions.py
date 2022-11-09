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


EXCEPTION_MESSAGE_MAP = {
    "Authorization is required": LaMetricAuthenticationError,
}


def raise_on_data_error(
    data: dict[str, Any], raising_error: aiohttp.ClientResponseError
) -> None:
    """Raise an exception (if appropriate) based on response data.

    Args:
        data: An API response payload.
        raising_error: The original aiohttp.ClientResponseError.

    Raises:
        exc: An appropriate LaMetricError (or subclass).
    """
    if (errors := data.get("errors")) is None:
        return

    error = errors[0]
    exc = EXCEPTION_MESSAGE_MAP.get(error["message"], LaMetricError)
    exc.__cause__ = raising_error
    raise exc(error)
