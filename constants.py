from enum import Enum, IntEnum


class CacheConfig(IntEnum):
    EXPIRATION_TIME = 360


class TemperatureThresholds(IntEnum):
    AVERAGE = 80
    SINGLE = 80
    SINGLE_INCREASE_DELTA = 10
    AVERAGE_INCREASE_DELTA = 10


class HumidityThresholds(IntEnum):
    AVERAGE = 80
    SINGLE = 80
    SINGLE_INCREASE_DELTA = 10
    AVERAGE_INCREASE_DELTA = 10


class AirQualityThresholds(IntEnum):
    AVERAGE = 80
    SINGLE = 80
    SINGLE_INCREASE_DELTA = 10
    AVERAGE_INCREASE_DELTA = 10


class SensorType(Enum):
    TEMPERATURE = 1
    HUMIDITY = 2
    AIRQUALITY = 3


class NotificationType(Enum):
    TOO_HIGH_SINGLE = 1
    TOO_LOW_SINGLE = 2
    RAPID_INCREASE = 3
    RAPID_DECREASE = 4
    TOO_HIGH_AVERAGE = 5
    TOO_LOW_AVERAGE = 6
    NONE = 7
