"""Models for LaMetric."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from ipaddress import IPv4Address
from typing import Any

from awesomeversion import AwesomeVersion
from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin

from .const import (
    DEVICE_MODELS,
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

    available: bool = True
    volume: int | None
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
class DisplayScreensaverTimeBased(DataClassORJSONMixin):
    """Object holding the time based screensaver mode of an LaMetric device."""

    enabled: bool
    end_time: time | None = None
    start_time: time | None = None

    # Derived by the device from start_time/end_time, which are in GMT.
    local_end_time: time | None = None
    local_start_time: time | None = None


@dataclass(kw_only=True)
class DisplayScreensaverWhenDark(DataClassORJSONMixin):
    """Object holding the when dark screensaver mode of an LaMetric device."""

    enabled: bool


@dataclass(kw_only=True)
class DisplayScreensaverModes(DataClassORJSONMixin):
    """Object holding the screensaver modes of an LaMetric device."""

    time_based: DisplayScreensaverTimeBased
    when_dark: DisplayScreensaverWhenDark


@dataclass(kw_only=True)
class DisplayScreensaver(DataClassORJSONMixin):
    """Object holding the screensaver data of an LaMetric device."""

    enabled: bool
    modes: DisplayScreensaverModes | None = None
    widget: str | None = None


@dataclass(kw_only=True)
class Display(DataClassORJSONMixin):
    """Object holding the display state of an LaMetric device."""

    brightness: int
    brightness_mode: BrightnessMode
    brightness_range: Range | None = None
    brightness_limit: Range | None = None
    display_type: DisplayType | None = field(
        default=None, metadata=field_options(alias="type")
    )
    height: int
    on: bool | None = None
    screensaver: DisplayScreensaver | None = None
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

    audio: Audio | None = None
    bluetooth: Bluetooth | None = None
    device_id: str = field(metadata=field_options(alias="id"))
    display: Display
    mode: DeviceMode
    model: str
    name: str
    os_version: AwesomeVersion
    serial_number: str
    update: Update | None = field(
        metadata=field_options(alias="update_available"), default=None
    )
    wifi: Wifi

    @property
    def model_name(self) -> str | None:
        """Return the product name for the reported model.

        None if the reported model is not a known one.
        """
        return DEVICE_MODELS.get(self.model)


@dataclass(kw_only=True)
class Update(DataClassORJSONMixin):
    """Object holding the update state of an LaMetric device."""

    version: AwesomeVersion


@dataclass(kw_only=True)
class AppParameter(DataClassORJSONMixin):
    """Object holding a parameter of an app action or trigger."""

    data_type: str
    name: str

    # A regular expression the value has to match, when the device
    # constrains it.
    format: str | None = None

    # Absent on trigger parameters.
    required: bool | None = None


@dataclass(kw_only=True)
class Widget(DataClassORJSONMixin):
    """Object holding a widget of an app on an LaMetric device."""

    index: int
    package: str

    # Free form, and specific to the app it belongs to.
    settings: dict[str, Any] = field(default_factory=dict)

    # Only reported when listing all apps.
    visible: bool | None = None


@dataclass(kw_only=True)
class App(DataClassORJSONMixin):
    """Object holding an app installed on an LaMetric device."""

    package: str
    title: str
    vendor: str
    version: AwesomeVersion
    version_code: str

    # Keyed by action or trigger name, holding their parameters by name.
    # Apps without any actions leave the key out entirely.
    actions: dict[str, dict[str, AppParameter]] = field(default_factory=dict)
    triggers: dict[str, dict[str, AppParameter]] = field(default_factory=dict)

    # Keyed by widget ID.
    widgets: dict[str, Widget] = field(default_factory=dict)


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

    class Config(BaseConfig):
        """Simple model configuration."""

        omit_none = True


@dataclass(kw_only=True)
class GoalData(DataClassORJSONMixin):
    """Object holding the goal data of an LaMetric notification."""

    current: int
    end: int
    start: int
    unit: str | None = None

    class Config(BaseConfig):
        """Goal data model configuration."""

        omit_none = True


@dataclass(kw_only=True)
class Goal(DataClassORJSONMixin):
    """Object holding the goal frame of an LaMetric notification."""

    data: GoalData = field(metadata=field_options(alias="goalData"))
    icon: int | str | None = None

    class Config(BaseConfig):
        """Goal model configuration."""

        omit_none = True
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
class SoundURL(DataClassORJSONMixin):
    """Sound URL model configuration."""

    url: str
    type: str = "mp3"
    fallback: Sound | None = None

    class Config(BaseConfig):
        """Sound URL model configuration."""

        omit_none = True


@dataclass(kw_only=True)
class Model(DataClassORJSONMixin):
    """Object holding the notification model of an LaMetric device."""

    cycles: int = 1
    frames: list[Chart | Goal | Simple]
    sound: SoundURL | Sound | None = None

    class Config(BaseConfig):
        """Model configuration."""

        omit_none = True


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
