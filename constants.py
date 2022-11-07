from enum import Enum, IntEnum
from typing import Type, List, Union
from dataclasses import dataclass, field


class CacheConfig(IntEnum):
    EXPIRATION_TIME = 360


class SensorTypes(IntEnum):
    TEMPERATURE = 1
    HUMIDITY = 2
    AIRQUALITY = 3


@dataclass
class SensorConfig:
    sensor_type: SensorTypes
    thresholds: dict = field(init=False)

    def __post_init__(self):
        if self.sensor_type == SensorTypes.TEMPERATURE:
            self.thresholds = {
                "average": 80,
                "single_reading_limit": 80,
                "single_increase_change": 10,
                "average_increase_change": 10,
            }
        elif self.sensor_type == SensorTypes.HUMIDITY:
            self.thresholds = {
                "average": 30,
                "single_reading_limit": 50,
                "single_increase_change": 5,
                "average_increase_change": 5,
            }
        elif self.sensor_type == SensorTypes.AIRQUALITY:
            self.thresholds = {
                "average": 35,
                "single_reading_limit": 90,
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


# sensor_configs: List[
#     tuple[Union[Type[Temperature], Type[Humidity], Type[AirQuality]], SensorTypes]
# ] = [
#     (Temperature, SensorTypes.TEMPERATURE),
#     (Humidity, SensorTypes.HUMIDITY),
#     (AirQuality, SensorTypes.AIRQUALITY),
# ]
