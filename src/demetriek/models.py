"""Models for LaMetric."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import IPv4Address

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


@dataclass(kw_only=True)
class Range(DataClassORJSONMixin):
    """Object holding an integer range."""

    range_max: int = field(metadata=field_options(alias="max"))
    range_min: int = field(metadata=field_options(alias="min"))


@dataclass(kw_only=True)
class Audio(DataClassORJSONMixin):
    """Object holding the audio state of an LaMetric device."""

    volume: int
    volume_limit: Range | None
    volume_range: Range | None


@dataclass(kw_only=True)
class Bluetooth(DataClassORJSONMixin):
    """Object holding the Bluetooth state of an LaMetric device."""

    active: bool
    address: str
    available: bool
    discoverable: bool
    name: str
    pairable: bool


@dataclass(kw_only=True)
class DisplayScreensaver(DataClassORJSONMixin):
    """Object holding the screensaver data of an LaMetric device."""

    enabled: bool


@dataclass(kw_only=True)
class Display(DataClassORJSONMixin):
    """Object holding the display state of an LaMetric device."""

    brightness: int
    brightness_mode: BrightnessMode
    display_type: DisplayType | None = field(
        default=None, metadata=field_options(alias="type")
    )
    height: int
    screensaver: DisplayScreensaver
    width: int


@dataclass(kw_only=True)
class Wifi(DataClassORJSONMixin):
    """Object holding the Wi-Fi state of an LaMetric device."""

    active: bool
    available: bool
    encryption: str | None = None
    ip: IPv4Address
    mac: str
    mode: WifiMode
    netmask: str
    rssi: int | None = None
    ssid: str


@dataclass(kw_only=True)
class Device(DataClassORJSONMixin):
    """Object holding the state of an LaMetric device."""

    audio: Audio
    bluetooth: Bluetooth
    device_id: str = field(metadata=field_options(alias="id"))
    display: Display
    mode: DeviceMode
    model: str
    name: str
    os_version: AwesomeVersion
    serial_number: str
    wifi: Wifi


@dataclass(kw_only=True)
class Chart(DataClassORJSONMixin):
    """Object holding the chart frame of an LaMetric notification."""

    data: list[int] = field(metadata=field_options(alias="chartData"))

    class Config(BaseConfig):
        """Chart model configuration."""

        serialize_by_alias = True
        allow_deserialization_not_by_alias = True


@dataclass(kw_only=True)
class Simple(DataClassORJSONMixin):
    """Object holding the simple frame of an LaMetric notification."""

    icon: int | str | None = None
    text: str


@dataclass(kw_only=True)
class GoalData(DataClassORJSONMixin):
    """Object holding the goal data of an LaMetric notification."""

    current: int
    end: int
    start: int
    unit: str | None = None


@dataclass(kw_only=True)
class Goal(DataClassORJSONMixin):
    """Object holding the goal frame of an LaMetric notification."""

    data: GoalData = field(metadata=field_options(alias="goalData"))
    icon: int | str | None = None

    class Config(BaseConfig):
        """Goal model configuration."""

        serialize_by_alias = True
        allow_deserialization_not_by_alias = True


@dataclass(kw_only=True)
class Sound(DataClassORJSONMixin):
    """Object holding the notification sound state of an LaMetric device."""

    category: NotificationSoundCategory | None = None
    repeat: int = 1
    sound: AlarmSound | NotificationSound = field(metadata=field_options(alias="id"))

    def __post_init__(self) -> None:
        """Infer the category of the sound."""
        if self.category is not None:
            return

        if self.sound in AlarmSound:
            self.category = NotificationSoundCategory.ALARMS

        if self.sound in NotificationSound:
            self.category = NotificationSoundCategory.NOTIFICATIONS

    class Config(BaseConfig):
        """Sound model configuration."""

        serialize_by_alias = True
        allow_deserialization_not_by_alias = True


@dataclass(kw_only=True)
class Model(DataClassORJSONMixin):
    """Object holding the notification model of an LaMetric device."""

    cycles: int = 1
    frames: list[Chart | Goal | Simple]
    sound: Sound | None = None


@dataclass(kw_only=True)
class Notification(DataClassORJSONMixin):
    """Object holding a LaMetric notification."""

    created: datetime | None = None
    expiration_date: datetime | None = None
    icon_type: NotificationIconType | None = None
    life_time: float | None = None
    model: Model
    notification_id: int | None = field(
        default=None,
        metadata=field_options(alias="id"),
    )
    notification_type: NotificationType | None = field(
        default=None,
        metadata=field_options(alias="type"),
    )
    priority: NotificationPriority | None = None

    class Config(BaseConfig):
        """Notification model configuration."""

        serialize_by_alias = True
        omit_none = True


@dataclass(kw_only=True)
class User(DataClassORJSONMixin):
    """Object holding LaMetric User information."""

    apps_count: int
    email: str
    name: str
    private_apps_count: int
    private_device_count: int
    user_id: int = field(metadata=field_options(alias="id"))


@dataclass(kw_only=True)
class CloudDevice(DataClassORJSONMixin):
    """Object holding the state of an LaMetric device from the Cloud."""

    api_key: str
    created_at: datetime
    device_id: int = field(metadata=field_options(alias="id"))
    ip: IPv4Address = field(metadata=field_options(alias="ipv4_internal"))
    mac: str
    name: str
    serial_number: str
    ssid: str = field(metadata=field_options(alias="wifi_ssid"))
    state: DeviceState
    updated_at: datetime
