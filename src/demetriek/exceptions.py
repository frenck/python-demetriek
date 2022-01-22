"""Exceptions for LaMetric."""


class LaMetricError(Exception):
    """Generic LaMetric exception."""


class LaMetricConnectionError(LaMetricError):
    """LaMetric connection exception."""


class LaMetricConnectionTimeoutError(LaMetricConnectionError):
    """LaMetric connection Timeout exception."""
