"""Asynchronous Python client for LaMetric TIME devices."""

import asyncio
import socket

import pytest
from aioresponses import aioresponses

from demetriek import (
    LaMetricConnectionError,
    LaMetricDevice,
    LaMetricError,
    LaMetricStream,
    StreamArea,
    StreamContentEncoding,
    StreamFadingPixels,
    StreamFillType,
    StreamRenderMode,
    StreamSession,
    StreamStatus,
    build_lmsp_packet,
)

from .conftest import DEVICE_URL, load_fixture, request_json

STREAM_URL = f"{DEVICE_URL}/api/v2/device/stream"
SESSION_ID = "a2891aa891ab4f8e8a1a16eb319b00f3"

# The header of the LMSP example in the documentation, for a 24x8 raw frame.
DOCUMENTED_HEADER = bytes(
    [
        0x6C, 0x6D, 0x73, 0x70,  # "lmsp"
        0x01, 0x00,  # Version 1
        0xA2, 0x89, 0x1A, 0xA8, 0x91, 0xAB, 0x4F, 0x8E,  # Session ID
        0x8A, 0x1A, 0x16, 0xEB, 0x31, 0x9B, 0x00, 0xF3,
        0x00,  # Raw data
        0x00,  # Reserved
        0x01,  # One area
        0x00,  # Reserved
        0x00, 0x00,  # x = 0
        0x00, 0x00,  # y = 0
        0x18, 0x00,  # width = 24
        0x08, 0x00,  # height = 8
        0x40, 0x02,  # data length = 576
    ]
)  # fmt: skip


async def test_stream(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting the stream state of a TIME."""
    responses.get(STREAM_URL, status=200, body=load_fixture("stream.json"))

    stream = await device.stream()

    assert stream.status is StreamStatus.STOPPED
    assert stream.protocol == "lmsp"
    assert stream.version == "1.0"
    assert stream.port == 9999
    assert stream.features == []
    assert stream.canvas.pixel
    assert stream.canvas.pixel.size.width == 37
    assert stream.canvas.pixel.size.height == 8
    assert stream.canvas.triangle is None


async def test_stream_triangle(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test getting the stream state of a SKY, which has triangular pixels."""
    responses.get(STREAM_URL, status=200, body=load_fixture("stream_sky.json"))

    stream = await device.stream()

    assert stream.canvas.triangle
    assert stream.canvas.triangle.size.width == 48
    assert stream.canvas.triangle.size.height == 16


async def test_stream_start(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test starting a stream with the default settings."""
    url = f"{STREAM_URL}/start"
    responses.put(url, status=200, body=load_fixture("stream_start.json"))

    session = await device.stream_start()

    assert request_json(responses, "PUT", url) == {
        "canvas": {
            "fill_type": "scale",
            "render_mode": "pixel",
            "post_process": {"type": "none"},
        }
    }
    assert session == StreamSession(
        fill_type=StreamFillType.SCALE,
        port=9999,
        render_mode=StreamRenderMode.PIXEL,
        session_id=SESSION_ID,
        status=StreamStatus.RECEIVING,
    )


async def test_stream_start_fading_pixels(
    responses: aioresponses, device: LaMetricDevice
) -> None:
    """Test starting a stream with the fading pixels effect."""
    url = f"{STREAM_URL}/start"
    responses.put(url, status=200, body=load_fixture("stream_start.json"))

    await device.stream_start(
        fill_type=StreamFillType.TILE,
        render_mode=StreamRenderMode.TRIANGLE,
        fading_pixels=StreamFadingPixels(fade_speed=0.01),
    )

    assert request_json(responses, "PUT", url) == {
        "canvas": {
            "fill_type": StreamFillType.TILE,
            "render_mode": StreamRenderMode.TRIANGLE,
            "post_process": {
                "type": "effect",
                "params": {
                    "effect_type": "fading_pixels",
                    "effect_params": {
                        "fade_speed": 0.01,
                        "pixel_base": 0.05,
                        "pixel_fill": 1,
                        "smooth": True,
                    },
                },
            },
        }
    }


async def test_stream_stop(responses: aioresponses, device: LaMetricDevice) -> None:
    """Test stopping a stream."""
    url = f"{STREAM_URL}/stop"
    responses.put(url, status=200, body=load_fixture("stream_stop.json"))

    await device.stream_stop()

    assert len(responses.requests) == 1


def test_build_lmsp_packet() -> None:
    """Test a packet matches the example in the LMSP documentation."""
    frame = bytes(24 * 8 * 3)

    packet = build_lmsp_packet(
        session_id=SESSION_ID,
        areas=[StreamArea(data=frame, width=24, height=8)],
    )

    assert packet == DOCUMENTED_HEADER + frame


def test_build_lmsp_packet_multiple_areas() -> None:
    """Test every area gets its own position, size, and data."""
    packet = build_lmsp_packet(
        session_id=SESSION_ID,
        areas=[
            StreamArea(data=bytes(3), width=1, height=1),
            StreamArea(data=b"\xff" * 6, width=2, height=1, x=5, y=7),
        ],
    )

    # Header (26 bytes), first area (10 + 3 bytes), second area (10 + 6 bytes).
    assert len(packet) == 26 + 13 + 16
    assert packet[24] == 2
    assert packet[39:49] == b"\x05\x00\x07\x00\x02\x00\x01\x00\x06\x00"
    assert packet[49:] == b"\xff" * 6


def test_build_lmsp_packet_encoded() -> None:
    """Test encoded data is not checked against the area size."""
    packet = build_lmsp_packet(
        session_id=SESSION_ID,
        areas=[StreamArea(data=b"\x89PNG", width=24, height=8)],
        encoding=StreamContentEncoding.PNG,
    )

    assert packet[22] == StreamContentEncoding.PNG
    assert packet.endswith(b"\x89PNG")


@pytest.mark.parametrize(
    ("areas", "match"),
    [
        ([], "at least one area"),
        ([StreamArea(data=bytes(10), width=2, height=2)], "must be 12 bytes"),
        (
            [StreamArea(data=bytes(255 * 255 * 3), width=255, height=255)],
            "does not fit in one area",
        ),
        (
            [StreamArea(data=bytes(3), width=1, height=1)] * 256,
            "at most 255 areas",
        ),
        (
            [StreamArea(data=bytes(3), width=1, height=1, x=-1)],
            "x must be between 0 and 65535, got -1",
        ),
        (
            [StreamArea(data=bytes(3), width=1, height=1, y=65536)],
            "y must be between 0 and 65535, got 65536",
        ),
        (
            [StreamArea(data=b"", width=-1, height=0)],
            "width must be between 0 and 65535, got -1",
        ),
        (
            [StreamArea(data=b"", width=0, height=-1)],
            "height must be between 0 and 65535, got -1",
        ),
    ],
)
def test_build_lmsp_packet_invalid(areas: list[StreamArea], match: str) -> None:
    """Test packets that cannot be sent are rejected."""
    with pytest.raises(ValueError, match=match):
        build_lmsp_packet(session_id=SESSION_ID, areas=areas)


def test_build_lmsp_packet_too_large() -> None:
    """Test areas that fit on their own, but not together, are rejected."""
    area = StreamArea(data=bytes(40000), width=24, height=8)

    with pytest.raises(ValueError, match="does not fit in one datagram"):
        build_lmsp_packet(
            session_id=SESSION_ID,
            areas=[area, area],
            encoding=StreamContentEncoding.PNG,
        )


def _session(port: int) -> StreamSession:
    """Create a session pointing at a local port."""
    return StreamSession(
        fill_type=StreamFillType.SCALE,
        port=port,
        render_mode=StreamRenderMode.PIXEL,
        session_id=SESSION_ID,
        status=StreamStatus.RECEIVING,
    )


async def test_stream_send() -> None:
    """Test frames arrive as LMSP packets on the UDP port of the session."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.setblocking(False)  # noqa: FBT003
        port = receiver.getsockname()[1]
        frame = bytes(24 * 8 * 3)

        async with LaMetricStream(host="127.0.0.1", session=_session(port)) as stream:
            # Connecting twice keeps the same socket.
            await stream.connect()
            stream.send(frame, width=24, height=8)

            loop = asyncio.get_running_loop()
            packet = await asyncio.wait_for(loop.sock_recv(receiver, 2048), 5)

    assert packet == DOCUMENTED_HEADER + frame


@pytest.mark.parametrize(
    "exception", [socket.gaierror(), OSError("Socket unavailable")]
)
async def test_stream_connect_error(
    monkeypatch: pytest.MonkeyPatch, exception: OSError
) -> None:
    """Test a socket that cannot be opened raises a connection error."""

    async def fail(*_args: object, **_kwargs: object) -> None:
        raise exception

    monkeypatch.setattr(asyncio.get_running_loop(), "create_datagram_endpoint", fail)
    stream = LaMetricStream(host="lametric.invalid", session=_session(9999))

    with pytest.raises(LaMetricConnectionError, match=r"at lametric\.invalid"):
        await stream.connect()


async def test_stream_send_not_connected() -> None:
    """Test sending before connecting raises an error."""
    stream = LaMetricStream(host="127.0.0.1", session=_session(9999))

    with pytest.raises(LaMetricError, match="not connected"):
        stream.send(bytes(3), width=1, height=1)

    # Closing a stream that never connected is harmless.
    stream.close()
