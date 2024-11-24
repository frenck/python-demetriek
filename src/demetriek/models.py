"""Models for LaMetric."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any

from awesomeversion import AwesomeVersion
from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin

from .const import (
    AlarmSound,
    BrightnessMode,
    DeviceMode,
    DeviceState,
    DisplayType,
    NotificationIconType,
    NotificationPriority,
    NotificationSound,
    NotificationSoundCategory,
    NotificationType,
    WifiMode,
)


@dataclass
class Range(DataClassORJSONMixin):
    """Object holding an integer range."""

    range_min: int = field(metadata=field_options(alias="min"))
    range_max: int = field(metadata=field_options(alias="max"))


@dataclass
class Audio(DataClassORJSONMixin):
    """Object holding the audio state of an LaMetric device."""

    volume: int
    volume_range: Range | None
    volume_limit: Range | None


@dataclass
class Bluetooth(DataClassORJSONMixin):
    """Object holding the Bluetooth state of an LaMetric device."""

    available: bool
    name: str
    active: bool
    discoverable: bool
    pairable: bool
    address: str


@dataclass
class DisplayScreensaver(DataClassORJSONMixin):
    """Object holding the screensaver data of an LaMetric device."""

    enabled: bool


@dataclass
class Display(DataClassORJSONMixin):
    """Object holding the display state of an LaMetric device."""

    brightness: int
    brightness_mode: BrightnessMode
    width: int
    height: int
    screensaver: DisplayScreensaver
    display_type: DisplayType | None = field(
        default=None,
        metadata=field_options(alias="type"),
    )


@dataclass
class Wifi(DataClassORJSONMixin):
    """Object holding the Wi-Fi state of an LaMetric device."""

    active: bool
    mac: str
    available: bool
    ssid: str
    ip: IPv4Address
    mode: WifiMode
    netmask: str
    encryption: str | None = None
    rssi: int | None = None


@dataclass
class Device(DataClassORJSONMixin):
    """Object holding the state of an LaMetric device."""

    device_id: str = field(metadata=field_options(alias="id"))
    name: str
    serial_number: str
    os_version: AwesomeVersion
    mode: DeviceMode
    model: str
    audio: Audio
    bluetooth: Bluetooth
    display: Display
    wifi: Wifi


@dataclass
class Chart(DataClassORJSONMixin):
    """Object holding the chart frame of an LaMetric notification."""

    data: list[int] = field(metadata=field_options(alias="chartData"))

    class Config(BaseConfig):
        """Chart model configuration."""

        allow_deserialization_not_by_alias = True


@dataclass
class Simple(DataClassORJSONMixin):
    """Object holding the simple frame of an LaMetric notification."""

    text: str
    icon: int | str | None = None


@dataclass
class GoalData(DataClassORJSONMixin):
    """Object holding the goal data of an LaMetric notification."""

    current: int
    end: int
    start: int
    unit: str | None = None


@dataclass
class Goal(DataClassORJSONMixin):
    """Object holding the goal frame of an LaMetric notification."""

    data: GoalData = field(metadata=field_options(alias="goalData"))
    icon: int | str | None = None

    class Config(BaseConfig):
        """Goal model configuration."""

        allow_deserialization_not_by_alias = True


@dataclass
class Sound(DataClassORJSONMixin):
    """Object holding the notification sound state of an LaMetric device."""

    sound: AlarmSound | NotificationSound = field(metadata=field_options(alias="id"))
    repeat: int = 1
    category: NotificationSoundCategory | None = None

    @classmethod
    def __pre_deserialize__(cls, d: dict[Any, Any]) -> dict[Any, Any]:
        """Infer the category of the sound.

        Args:
        ----
            values: The values of the model.

        Returns:
        -------
            The values of the model, with the category field inferred.

        """
        if d["category"] is not None:
            return d

        if d["sound"] in AlarmSound:
            d["category"] = NotificationSoundCategory.ALARMS

        if d["sound"] in NotificationSound:
            d["category"] = NotificationSoundCategory.NOTIFICATIONS

        return d

    class Config(BaseConfig):
        """Sound model configuration."""

        allow_deserialization_not_by_alias = True


@dataclass
class Model(DataClassORJSONMixin):
    """Object holding the notification model of an LaMetric device."""

    frames: list[Chart | Goal | Simple]
    sound: Sound | None = None
    cycles: int = 1


@dataclass
class Notification(DataClassORJSONMixin):
    """Object holding a LaMetric notification."""

    model: Model
    created: datetime | None = None
    expiration_date: datetime | None = None
    icon_type: NotificationIconType | None = None
    life_time: float | None = None
    priority: NotificationPriority | None = None
    notification_id: int | None = field(
        default=None,
        metadata=field_options(alias="id"),
    )
    notification_type: NotificationType | None = field(
        default=None,
        metadata=field_options(alias="type"),
    )


@dataclass
class User(DataClassORJSONMixin):
    """Object holding LaMetric User information."""

    apps_count: int
    email: str
    name: str
    private_apps_count: int
    private_device_count: int
    user_id: int = field(metadata=field_options(alias="id"))


@dataclass
class CloudDevice(DataClassORJSONMixin):
    """Object holding the state of an LaMetric device from the Cloud."""

    device_id: int = field(metadata=field_options(alias="id"))
    name: str
    state: DeviceState
    serial_number: str
    api_key: str
    ip: IPv4Address = field(metadata=field_options(alias="ipv4_internal"))
    mac: str
    ssid: str = field(metadata=field_options(alias="wifi_ssid"))
    created_at: datetime
    updated_at: datetime
