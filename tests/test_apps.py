"""Asynchronous Python client for LaMetric TIME devices."""
# pylint: disable=protected-access
import aiohttp
from aresponses import ResponsesMockServer

from demetriek import LaMetricDevice

from . import load_fixture


async def test_app_next(aresponses: ResponsesMockServer) -> None:
    """Test switching to the next app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/next",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps_next.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_next()


async def test_app_previous(aresponses: ResponsesMockServer) -> None:
    """Test switching to the previous app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/prev",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps_prev.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_previous()
