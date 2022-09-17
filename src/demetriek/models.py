"""Models for LaMetric."""
from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Optional, Union

from awesomeversion import AwesomeVersion
from pydantic import BaseModel, Field, root_validator

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


class Range(BaseModel):
    """Object holding an integer range."""

    range_min: int = Field(..., alias="min")
    range_max: int = Field(..., alias="max")


class Audio(BaseModel):
    """Object holding the audio state of an LaMetric device."""

    volume: int
    volume_range: Optional[Range]
    volume_limit: Optional[Range]


class Bluetooth(BaseModel):
    """Object holding the Bluetooth state of an LaMetric device."""

    available: bool
    name: str
    active: bool
    discoverable: bool
    pairable: bool
    address: str


class Display(BaseModel):
    """Object holding the display state of an LaMetric device."""

    brightness: int
    brightness_mode: BrightnessMode
    width: int
    height: int
    display_type: DisplayType = Field(None, alias="type")


class Wifi(BaseModel):
    """Object holding the Wi-Fi state of an LaMetric device."""

    active: bool
    mac: str
    available: bool
    encryption: Optional[str] = None
    ssid: str
    ip: IPv4Address
    mode: WifiMode
    netmask: str
    rssi: Optional[int] = None


class Device(BaseModel):
    """Object holding the state of an LaMetric device."""

    device_id: str = Field(..., alias="id")
    name: str
    serial_number: str
    os_version: AwesomeVersion
    mode: DeviceMode
    model: str
    audio: Audio
    bluetooth: Bluetooth
    display: Display
    wifi: Wifi


class Chart(BaseModel):
    """Object holding the chart frame of an LaMetric notification."""

    data: list[int] = Field(..., alias="chartData")

    class Config:
        """Chart model configuration."""

        allow_population_by_field_name = True


class Simple(BaseModel):
    """Object holding the simple frame of an LaMetric notification."""

    icon: Optional[Union[int, str]] = None
    text: str


class GoalData(BaseModel):
    """Object holding the goal data of an LaMetric notification."""

    current: int
    end: int
    start: int
    unit: Optional[str] = None


class Goal(BaseModel):
    """Object holding the goal frame of an LaMetric notification."""

    icon: Optional[Union[int, str]] = None
    data: GoalData = Field(..., alias="goalData")

    class Config:
        """Goal model configuration."""

        allow_population_by_field_name = True


class Sound(BaseModel):
    """Object holding the notification sound state of an LaMetric device."""

    category: Optional[NotificationSoundCategory]
    sound: Union[AlarmSound, NotificationSound] = Field(..., alias="id")
    repeat: int = 1

    @root_validator
    @classmethod
    def infer_category(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: F841
        """Infer the category of the sound.

        Args:
            values: The values of the model.

        Returns:
            The values of the model, with the category field inferred.
        """
        if values["category"] is not None:
            return values

        if values["sound"] in AlarmSound:
            values["category"] = NotificationSoundCategory.ALARMS

        if values["sound"] in NotificationSound:
            values["category"] = NotificationSoundCategory.NOTIFICATIONS

        return values

    class Config:
        """Sound model configuration."""

        allow_population_by_field_name = True


class Model(BaseModel):
    """Object holding the notification model of an LaMetric device."""

    frames: list[Union[Chart, Goal, Simple]]
    sound: Optional[Sound] = None
    cycles: int = 1


class Notification(BaseModel):
    """Object holding a LaMetric notification."""

    model: Model
    created: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    icon_type: Optional[NotificationIconType] = None
    life_time: Optional[float] = None
    priority: Optional[NotificationPriority] = None
    notification_id: Optional[int] = Field(None, alias="id")
    notification_type: Optional[NotificationType] = Field(None, alias="type")


class User(BaseModel):
    """Object holding LaMetric User information."""

    apps_count: int
    email: str
    name: str
    private_apps_count: int
    private_device_count: int
    user_id: int = Field(..., alias="id")


class CloudDevice(BaseModel):
    """Object holding the state of an LaMetric device from the Cloud."""

    device_id: int = Field(..., alias="id")
    name: str
    state: DeviceState
    serial_number: str
    api_key: str
    ip: IPv4Address = Field(..., alias="ipv4_internal")
    mac: str
    ssid: str = Field(..., alias="wifi_ssid")
    created_at: datetime
    updated_at: datetime
