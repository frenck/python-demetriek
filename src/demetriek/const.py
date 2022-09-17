"""Asynchronous Python client for LaMetric TIME devices."""

from enum import Enum


class BrightnessMode(str, Enum):
    """Enum holding the available brightness modes."""

    AUTO = "auto"
    MANUAL = "manual"


class DeviceMode(str, Enum):
    """Enum holding the available device modes."""

    AUTO = "auto"
    KIOSK = "kiosk"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class DeviceState(str, Enum):
    """Enum holding the available device states."""

    BANNED = "banned"
    CONFIGURED = "configured"
    NEW = "new"


class DisplayType(str, Enum):
    """Enum holding the available display types."""

    COLOR = "color"
    GRAYSCALE = "grayscale"
    MIXED = "mixed"
    MONOCHROME = "monochrome"


class NotificationIconType(str, Enum):
    """Enum holding the available icon types."""

    ALERT = "alert"
    INFO = "info"
    NONE = "none"


class NotificationPriority(str, Enum):
    """Enum holding the available notification priorities."""

    CRITICAL = "critical"
    INFO = "info"
    WARNING = "warning"


class NotificationSoundCategory(str, Enum):
    """Enum holding the available notification sound categories."""

    ALARMS = "alarms"
    NOTIFICATIONS = "notifications"


class AlarmSound(str, Enum):
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


class NotificationSound(str, Enum):
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


class NotificationType(str, Enum):
    """Enum holding the available notification types."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class WifiMode(str, Enum):
    """Enum holding the available Wi-Fi modes."""

    DHCP = "dhcp"
    STATIC = "static"
