"""Asynchronous Python client for LaMetric devices."""

from dataclasses import asdict

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from demetriek import LaMetricDevice
from demetriek.exceptions import LaMetricUnsupportedError

from . import load_fixture


async def test_widget(
    aresponses: ResponsesMockServer, snapshot: SnapshotAssertion
) -> None:
    """Test getting widget details."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("widget.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        widget = await demetriek.widget(
            package="com.lametric.clock", widget_id="08b8eac21074f8f7e5a29f2855ba8060"
        )

    assert widget is not None
    assert widget.package == "com.lametric.clock"
    assert widget.index == 0
    assert widget.visible is True
    assert asdict(widget) == snapshot


async def test_widget_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test widget API not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060",
        "GET",
        aresponses.Response(
            status=404,
            headers={"Content-Type": "application/json"},
            text='{"errors": [{"message": "Not found"}]}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        widget = await demetriek.widget(
            package="com.lametric.clock", widget_id="08b8eac21074f8f7e5a29f2855ba8060"
        )

    # Should return None for unsupported API
    assert widget is None


async def test_widget_action(aresponses: ResponsesMockServer) -> None:
    """Test triggering a widget action."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060/actions",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("widget_action.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        await demetriek.widget_action(
            package="com.lametric.clock",
            widget_id="08b8eac21074f8f7e5a29f2855ba8060",
            action_id="clock.clockface",
            parameters={"type": "weather"},
            activate=True,
        )


async def test_widget_action_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test widget_action not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060/actions",
        "POST",
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
            await demetriek.widget_action(
                package="com.lametric.clock",
                widget_id="08b8eac21074f8f7e5a29f2855ba8060",
                action_id="clock.clockface",
                parameters={"type": "weather"},
            )


async def test_widget_update(
    aresponses: ResponsesMockServer, snapshot: SnapshotAssertion
) -> None:
    """Test updating widget settings."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("widget_update.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        widget = await demetriek.widget_update(
            package="com.lametric.clock",
            widget_id="08b8eac21074f8f7e5a29f2855ba8060",
            settings={"time_format": "HH:mm:ss", "date_format": "MM/DD/YYYY"},
        )

    assert widget.package == "com.lametric.clock"
    assert widget.settings is not None
    assert widget.settings["time_format"] == "HH:mm:ss"
    assert asdict(widget) == snapshot


async def test_widget_update_unsupported(aresponses: ResponsesMockServer) -> None:
    """Test widget_update not supported (404 response)."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/apps/com.lametric.clock/widgets/08b8eac21074f8f7e5a29f2855ba8060",
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
            await demetriek.widget_update(
                package="com.lametric.clock",
                widget_id="08b8eac21074f8f7e5a29f2855ba8060",
                settings={"time_format": "HH:mm:ss"},
            )
