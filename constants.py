from enum import Enum, IntEnum
from dataclasses import dataclass, field


class CacheConfig(IntEnum):
    EXPIRATION_TIME = 360


class AlertTiming(IntEnum):
    AVERAGE_ALERT_WINDOW = 300


class SensorTypes(IntEnum):
    TEMPERATURE = 1
    HUMIDITY = 2
    AIRQUALITY = 3


@dataclass
class SensorConfig:
    sensor_type: SensorTypes
    thresholds: dict[str, int] = field(init=False, default_factory=dict)

    def __post_init__(self):
        if self.sensor_type == SensorTypes.TEMPERATURE:
            self.thresholds = {
                "average": 80,
                "single_reading": 80,
                "single_increase_change": 10,
                "average_increase_change": 10,
            }
        elif self.sensor_type == SensorTypes.HUMIDITY:
            self.thresholds = {
                "average": 80,
                "single_reading": 90,
                "single_increase_change": 20,
                "average_increase_change": 20,
            }
        elif self.sensor_type == SensorTypes.AIRQUALITY:
            self.thresholds = {
                "average": 35,
                "single_reading": 90,
                "single_increase_change": 15,
                "average_increase_change": 15,
            }


class NotificationType(Enum):
    TOO_HIGH_SINGLE = 1
    TOO_LOW_SINGLE = 2
    RAPID_INCREASE = 3
    RAPID_DECREASE = 4
    TOO_HIGH_AVERAGE = 5
    TOO_LOW_AVERAGE = 6
    NOOP = 7
    RAPID_INCREASE_AVERAGE = 8
