"""Common fixtures and helpers for the LaMetric tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest
from aioresponses import aioresponses
from aioresponses import core as aioresponses_core
from yarl import URL

from demetriek import LaMetricCloud, LaMetricDevice

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

DEVICE_URL = "https://127.0.0.2:4343"
CLOUD_URL = "https://developer.lametric.com"

FIXTURES_DIR = Path(__file__).parent / "fixtures"

AIOHTTP_REQUIRES_STREAM_WRITER = (
    "stream_writer" in aiohttp.ClientResponse.__init__.__code__.co_varnames
)
AIOHTTP_STREAM_WRITER = SimpleNamespace(output_size=0)


class AioresponsesClientResponse(aioresponses_core.ClientResponse):
    """Backwards-compatible ClientResponse for aioresponses."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize and provide a stream_writer for aiohttp 3.14+."""
        kwargs.setdefault("stream_writer", AIOHTTP_STREAM_WRITER)
        super().__init__(*args, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def setup_aioresponses_aiohttp_compat() -> Generator[None, None, None]:
    """Patch aioresponses ClientResponse for aiohttp compatibility in tests."""
    if not AIOHTTP_REQUIRES_STREAM_WRITER:
        yield
        return

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            aioresponses_core,
            "ClientResponse",
            AioresponsesClientResponse,
        )
        yield


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the tenacity backoff instant during tests.

    Tenacity sleeps via ``asyncio.sleep``. Swapping in a zero delay version
    keeps the real retry logic, without the exponential wall-clock cost.
    """
    real_sleep = asyncio.sleep

    async def instant_sleep(_delay: float, result: Any = None) -> Any:
        return await real_sleep(0, result)

    monkeypatch.setattr(asyncio, "sleep", instant_sleep)


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def request_json(
    mocker: aioresponses,
    method: str,
    url: str,
    index: int = 0,
) -> Any:
    """Return the JSON body the client sent with a recorded request."""
    return mocker.requests[(method, URL(url))][index].kwargs["json"]


@pytest.fixture
def responses() -> Generator[aioresponses, None, None]:
    """Yield an aioresponses instance that patches aiohttp client sessions."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture
async def device() -> AsyncGenerator[LaMetricDevice, None]:
    """Yield a LaMetric device client on a shared session."""
    async with aiohttp.ClientSession() as session:
        yield LaMetricDevice(host="127.0.0.2", api_key="abc", session=session)


@pytest.fixture
async def cloud() -> AsyncGenerator[LaMetricCloud, None]:
    """Yield a LaMetric cloud client on a shared session."""
    async with aiohttp.ClientSession() as session:
        yield LaMetricCloud(token="abc", session=session)  # noqa: S106
