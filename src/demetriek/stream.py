"""Asynchronous Python client for LaMetric TIME devices."""

from __future__ import annotations

import asyncio
import struct
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from .const import StreamContentEncoding
from .exceptions import LaMetricConnectionError, LaMetricError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .models import StreamSession

LMSP_PROTOCOL = b"lmsp"
LMSP_VERSION = 1

# Raw frames are RGB888: one byte for red, green, and blue per pixel.
RAW_BYTES_PER_PIXEL = 3

# The largest payload a single UDP datagram can carry over IPv4.
MAX_DATAGRAM_SIZE = 65507

# Positions, sizes, and data lengths are unsigned 16 bit fields.
MAX_FIELD_VALUE = 0xFFFF

# The number of areas in a packet is an unsigned 8 bit field.
MAX_AREAS = 0xFF


@dataclass(frozen=True, kw_only=True)
class StreamArea:
    """A rectangular part of the canvas, with the data to draw in it."""

    data: bytes
    height: int
    width: int
    x: int = 0
    y: int = 0


def build_lmsp_packet(
    *,
    session_id: str,
    areas: Sequence[StreamArea],
    encoding: StreamContentEncoding = StreamContentEncoding.RAW,
) -> bytes:
    """Build an LMSP packet, ready to be sent to the device over UDP.

    Args:
    ----
        session_id: Session ID of the stream, as returned when starting it.
        areas: Parts of the canvas to draw, each with its own data.
        encoding: Encoding of the data in every area.

    Returns:
    -------
        The packet as bytes.

    Raises:
    ------
        ValueError: The areas do not fit in a single packet, an area has a
            position or size out of range, or raw data does not match
            the size of its area.

    """
    if not areas:
        msg = "An LMSP packet needs at least one area"
        raise ValueError(msg)

    if len(areas) > MAX_AREAS:
        msg = f"An LMSP packet holds at most {MAX_AREAS} areas, got {len(areas)}"
        raise ValueError(msg)

    # Multi byte values in LMSP are little endian.
    packet = bytearray(LMSP_PROTOCOL)
    packet += struct.pack("<H", LMSP_VERSION)
    packet += uuid.UUID(hex=session_id).bytes
    packet += struct.pack("<BBBB", encoding, 0, len(areas), 0)

    for area in areas:
        fields = {"x": area.x, "y": area.y, "width": area.width, "height": area.height}
        for name, value in fields.items():
            if not 0 <= value <= MAX_FIELD_VALUE:
                msg = (
                    f"Area {name} must be between 0 and {MAX_FIELD_VALUE}, got {value}"
                )
                raise ValueError(msg)

        expected = area.width * area.height * RAW_BYTES_PER_PIXEL
        if encoding is StreamContentEncoding.RAW and len(area.data) != expected:
            msg = (
                f"Raw data for a {area.width}x{area.height} area must be"
                f" {expected} bytes, got {len(area.data)}"
            )
            raise ValueError(msg)

        if len(area.data) > MAX_FIELD_VALUE:
            msg = f"Area data of {len(area.data)} bytes does not fit in one area"
            raise ValueError(msg)

        packet += struct.pack(
            "<HHHHH", area.x, area.y, area.width, area.height, len(area.data)
        )
        packet += area.data

    if len(packet) > MAX_DATAGRAM_SIZE:
        msg = f"LMSP packet of {len(packet)} bytes does not fit in one datagram"
        raise ValueError(msg)

    return bytes(packet)


class LaMetricStream:
    """Send frames to a LaMetric device using LMSP over UDP.

    Start the stream with `LaMetricDevice.stream_start()` first, and stop it
    with `LaMetricDevice.stream_stop()` when done.
    """

    def __init__(
        self,
        *,
        host: str,
        session: StreamSession,
        encoding: StreamContentEncoding = StreamContentEncoding.RAW,
    ) -> None:
        """Initialize the stream.

        Args:
        ----
            host: Hostname or IP address of the LaMetric device.
            session: The session returned when starting the stream.
            encoding: Encoding of the frame data that will be sent.

        """
        self.host = host
        self.session = session
        self.encoding = encoding
        self._transport: asyncio.DatagramTransport | None = None

    async def connect(self) -> None:
        """Open the UDP socket to the device.

        Raises
        ------
            LaMetricConnectionError: The socket could not be opened, for
                example because the host could not be resolved.

        """
        if self._transport is not None:
            return

        loop = asyncio.get_running_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol,
                remote_addr=(self.host, self.session.port),
            )
        except OSError as exception:
            msg = f"Could not open a stream to the LaMetric device at {self.host}"
            raise LaMetricConnectionError(msg) from exception

    def send(self, frame: bytes, *, width: int, height: int) -> None:
        """Send a frame that covers the whole canvas.

        Args:
        ----
            frame: The frame data, RGB888 bytes when the encoding is raw.
            width: Width of the frame in pixels.
            height: Height of the frame in pixels.

        """
        self.send_areas([StreamArea(data=frame, width=width, height=height)])

    def send_areas(self, areas: Sequence[StreamArea]) -> None:
        """Send one or more parts of the canvas in a single packet.

        Args:
        ----
            areas: Parts of the canvas to draw.

        Raises:
        ------
            LaMetricError: The stream is not connected.

        """
        if self._transport is None:
            msg = "The stream is not connected, use connect() first"
            raise LaMetricError(msg)

        # UDP is fire and forget: a lost frame is simply replaced by the next.
        self._transport.sendto(
            build_lmsp_packet(
                session_id=self.session.session_id,
                areas=areas,
                encoding=self.encoding,
            )
        )

    def close(self) -> None:
        """Close the UDP socket."""
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The LaMetricStream object, connected to the device.

        """
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        self.close()
