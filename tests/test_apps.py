"""Asynchronous Python client for LaMetric devices."""

from dataclasses import asdict

import aiohttp
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from demetriek import LaMetricDevice

from . import load_fixture


async def test_apps(
    aresponses: ResponsesMockServer, snapshot: SnapshotAssertion
) -> None:
    """Test getting all apps."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("apps.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        apps = await demetriek.apps()

    assert apps is not None
    assert len(apps) == 2
    assert "com.lametric.clock" in apps
    assert "com.lametric.radio" in apps

    clock_app = apps["com.lametric.clock"]
    assert clock_app.title == "Clock"
    assert clock_app.vendor == "LaMetric"
    assert clock_app.version == "1.0.17"
    assert clock_app.widgets is not None
    assert len(clock_app.widgets) == 1

    # Verify snapshot
    apps_dict = {pkg: asdict(app) for pkg, app in apps.items()}
    assert apps_dict == snapshot


async def test_apps_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test apps API not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps",
        "GET",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        apps = await demetriek.apps()

    # Should return None for unsupported API
    assert apps is None
