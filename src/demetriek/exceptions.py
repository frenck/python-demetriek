"""Exceptions for LaMetric."""

from __future__ import annotations

import orjson


class LaMetricError(Exception):
    """Generic LaMetric exception."""


class LaMetricConnectionError(LaMetricError):
    """LaMetric connection exception."""


class LaMetricAuthenticationError(LaMetricError):
    """LaMetric authentication exception."""


class LaMetricConnectionTimeoutError(LaMetricConnectionError):
    """LaMetric connection Timeout exception."""


class LaMetricUnsupportedError(LaMetricError):
    """LaMetric device does not support what was asked of it."""


def error_message(body: str) -> str | None:
    """Extract the error messages from an error response of the LaMetric API.

    Both the device and the cloud answer errors with a body like
    `{"errors": [{"message": "..."}]}`. The web interface of the device
    answers with a single `{"error": {"message": "..."}}` instead.

    Args:
    ----
        body: The body of the error response.

    Returns:
    -------
        The error messages joined together, or None when the body holds none.

    """
    try:
        data = orjson.loads(body)
        errors = data.get("errors")
        if isinstance(error := data.get("error"), dict):
            errors = [error]
    except (ValueError, AttributeError):
        return None

    if not isinstance(errors, list):
        return None

    messages = [
        error["message"]
        for error in errors
        if isinstance(error, dict) and isinstance(error.get("message"), str)
    ]
    return "; ".join(messages) or None
