"""Asynchronous Python client for LaMetric TIME devices."""

from enum import IntEnum, StrEnum

# The model the device reports is a hardware identifier, not a product name.
# LaMetric TIME reports "LM 37X8" on firmware 2.x and "sa8" on 3.x.
DEVICE_MODELS: dict[str, str] = {
    "LM 37X8": "TIME",
    "sa5": "SKY",
    "sa8": "TIME",
}


class BrightnessMode(StrEnum):
    """Enum holding the available brightness modes."""

    AUTO = "auto"
    MANUAL = "manual"


class DeviceMode(StrEnum):
    """Enum holding the available device modes."""

    AUTO = "auto"
    KIOSK = "kiosk"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class DeviceState(StrEnum):
    """Enum holding the available device states."""

    BANNED = "banned"
    CONFIGURED = "configured"
    NEW = "new"


class DisplayType(StrEnum):
    """Enum holding the available display types."""

    COLOR = "color"
    GRAYSCALE = "grayscale"
    MIXED = "mixed"
    MONOCHROME = "monochrome"
    FULL_RGB = "full_rgb"


class NotificationIconType(StrEnum):
    """Enum holding the available icon types."""

    ALERT = "alert"
    INFO = "info"
    NONE = "none"


class NotificationPriority(StrEnum):
    """Enum holding the available notification priorities."""

    CRITICAL = "critical"
    INFO = "info"
    WARNING = "warning"


class NotificationSoundCategory(StrEnum):
    """Enum holding the available notification sound categories."""

    ALARMS = "alarms"
    NOTIFICATIONS = "notifications"


class AlarmSound(StrEnum):
    """Enum holding the available alarm sounds."""

    ALARM1 = "alarm1"
    ALARM2 = "alarm2"
    ALARM3 = "alarm3"
    ALARM4 = "alarm4"
    ALARM5 = "alarm5"
    ALARM6 = "alarm6"
    ALARM7 = "alarm7"
    ALARM8 = "alarm8"
    ALARM9 = "alarm9"
    ALARM10 = "alarm10"
    ALARM11 = "alarm11"
    ALARM12 = "alarm12"
    ALARM13 = "alarm13"


class NotificationSound(StrEnum):
    """Enum holding the available notification sounds."""

    BICYCLE = "bicycle"
    CAR = "car"
    CASH = "cash"
    CAT = "cat"
    DOG = "dog"
    DOG2 = "dog2"
    ENERGY = "energy"
    KNOCK_KNOCK = "knock-knock"
    LETTER_EMAIL = "letter_email"
    LOSE1 = "lose1"
    LOSE2 = "lose2"
    NEGATIVE1 = "negative1"
    NEGATIVE2 = "negative2"
    NEGATIVE3 = "negative3"
    NEGATIVE4 = "negative4"
    NEGATIVE5 = "negative5"
    # Misspelled names from older releases, kept as aliases.
    NETGATIVE1 = "negative1"
    NETGATIVE2 = "negative2"
    NETGATIVE3 = "negative3"
    NETGATIVE4 = "negative4"
    NETGATIVE5 = "negative5"
    NOTIFICATION = "notification"
    NOTIFICATION2 = "notification2"
    NOTIFICATION3 = "notification3"
    NOTIFICATION4 = "notification4"
    OPEN_DOOR = "open_door"
    POSITIVE1 = "positive1"
    POSITIVE2 = "positive2"
    POSITIVE3 = "positive3"
    POSITIVE4 = "positive4"
    POSITIVE5 = "positive5"
    POSITIVE6 = "positive6"
    STATISTIC = "statistic"
    THUNDER = "thunder"
    WATER1 = "water1"
    WATER2 = "water2"
    WIN = "win"
    WIN2 = "win2"
    WIND = "wind"
    WIND_SHORT = "wind_short"


class NotificationType(StrEnum):
    """Enum holding the available notification types."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class ScreensaverMode(StrEnum):
    """Enum holding the available screensaver modes."""

    SCREEN_OFF = "screen_off"
    TIME_BASED = "time_based"
    WHEN_DARK = "when_dark"


class StreamContentEncoding(IntEnum):
    """Enum holding the encodings LMSP accepts for frame data."""

    RAW = 0
    PNG = 1
    JPEG = 2
    GIF = 3


class StreamFillType(StrEnum):
    """Enum holding how a stream fills a screen larger than its canvas."""

    SCALE = "scale"
    TILE = "tile"


class StreamRenderMode(StrEnum):
    """Enum holding how streamed pixels map onto the screen."""

    PIXEL = "pixel"
    TRIANGLE = "triangle"


class StreamStatus(StrEnum):
    """Enum holding the available stream states."""

    RECEIVING = "receiving"
    STOPPED = "stopped"


class WifiMode(StrEnum):
    """Enum holding the available Wi-Fi modes."""

    DHCP = "dhcp"
    STATIC = "static"
