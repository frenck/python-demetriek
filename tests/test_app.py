"""Asynchronous Python client for LaMetric devices."""

from dataclasses import asdict

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from demetriek import LaMetricDevice
from demetriek.exceptions import LaMetricUnsupportedError

from . import load_fixture


async def test_app(
    aresponses: ResponsesMockServer, snapshot: SnapshotAssertion
) -> None:
    """Test getting specific app details."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        app = await demetriek.app(package="com.lametric.clock")

    assert app is not None
    assert app.title == "Clock"
    assert app.package == "com.lametric.clock"
    assert app.vendor == "LaMetric"
    assert asdict(app) == snapshot


async def test_app_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test app API not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock",
        "GET",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        app = await demetriek.app(package="com.lametric.clock")

    # Should return None for unsupported API
    assert app is None


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


async def test_app_next_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test app_next not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/next",
        "PUT",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)

        # Write operations should raise exception
        with pytest.raises(LaMetricUnsupportedError):
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


async def test_app_previous_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test app_previous not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/prev",
        "PUT",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)

        # Write operations should raise exception
        with pytest.raises(LaMetricUnsupportedError):
            await demetriek.app_previous()


async def test_app_activate(aresponses: ResponsesMockServer) -> None:
    """Test activating an app."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060/activate",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("app_activate.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.app_activate(
            package="com.lametric.clock", widget_id="08b8eac21074f8f7e5a29f2855ba8060"
        )


async def test_app_activate_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test app_activate not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060/activate",
        "PUT",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)

        # Write operations should raise exception
        with pytest.raises(LaMetricUnsupportedError):
            await demetriek.app_activate(
                package="com.lametric.clock",
                widget_id="08b8eac21074f8f7e5a29f2855ba8060",
            )
