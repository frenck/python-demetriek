"""Asynchronous Python client for LaMetric TIME devices."""

from dataclasses import asdict

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from demetriek import (
    Chart,
    Goal,
    GoalData,
    LaMetricDevice,
    Model,
    Notification,
    NotificationIconType,
    NotificationSound,
    Simple,
    Sound,
)
from demetriek.const import (
    NotificationType,
)

from . import load_fixture


@pytest.mark.parametrize(
    "fixture",
    [
        "device.json",
        "device2.json",
        "device3.json",
    ],
)
async def test_get_device(
    aresponses: ResponsesMockServer, fixture: str, snapshot: SnapshotAssertion
) -> None:
    """Test getting device information."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture(fixture),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        device = await demetriek.device()

    assert asdict(device) == snapshot


async def test_notify(aresponses: ResponsesMockServer) -> None:
    """Test sending notification serialization."""
    aresponses.add(
        "127.0.0.2:4343",
        "/api/v2/device/notifications",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("notification.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        demetriek = LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)
        notification = Notification(
            icon_type=NotificationIconType.ALERT,
            notification_type=NotificationType.EXTERNAL,
            model=Model(
                frames=[
                    Simple(text="Yeah", icon=18815),
                    Goal(
                        icon=7956,
                        data=GoalData(
                            current=65,
                            end=100,
                            start=0,
                            unit="%",
                        ),
                    ),
                    Chart(data=[1, 2, 3, 4, 5, 4, 3, 2, 1]),
                ],
                sound=Sound(sound=NotificationSound.WIN),
            ),
        )
        response = await demetriek.notify(notification=notification)

    # check response
    assert response == 1
    # check on serialized request if aliases are used and null values are removed
    request = await aresponses.history[0].request.json()
    assert request["type"] == "external"
    assert request["icon_type"] == "alert"
    assert "life_time" not in request
    assert request["model"]["sound"]["id"] == "win"
    assert request["model"]["sound"]["category"] == "notifications"
    assert request["model"]["frames"][0]["text"] == "Yeah"
    assert request["model"]["frames"][1]["goalData"]["current"] == 65
    assert request["model"]["frames"][2]["chartData"] == [1, 2, 3, 4, 5, 4, 3, 2, 1]
