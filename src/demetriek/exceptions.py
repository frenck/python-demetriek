"""Exceptions for LaMetric."""


class LaMetricError(Exception):
    """Generic LaMetric exception."""


class LaMetricConnectionError(LaMetricError):
    """LaMetric connection exception."""


class LaMetricAuthenticationError(LaMetricError):
    """LaMetric authentication exception."""


class LaMetricConnectionTimeoutError(LaMetricConnectionError):
    """LaMetric connection Timeout exception."""


class LaMetricUnsupportedError(LaMetricError):
    """LaMetric API feature not supported on this device version."""
