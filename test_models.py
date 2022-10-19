import pytest  # type: ignore

from constants import NotificationType, SensorType, TemperatureThresholds
from models import *
from main import *


@pytest.fixture
def example_temperature_event():
    temp = 95
    readings4 = NotecardReading(
        sensor_name="arduino_1", sensor_reading=temp, sensor_type=SensorType(1)
    )

    readings = NotecardEvent(
        datetime=1665021239,
        event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
        best_lat=45.5728875,
        best_long=-122.66610937499999,
        readings=[readings4],
    )

    return readings


@pytest.fixture
def example_temperature_reading(temp, average) -> Reading:
    return Reading(
        datetime=1665021239,
        event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
        best_lat=45.5728875,
        best_long=-122.66610937499999,
        sensor_name="arduino1",
        sensor_type=SensorType(1),
        sensor_reading=temp,
        recent_average=average,
    )


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            5 + TemperatureThresholds.SINGLE.value,
            TemperatureThresholds.AVERAGE.value - 5,
        ),
        (2000000000000000000, -56),
    ],
)
def test_temperature_too_high(example_temperature_reading):
    notification_event = Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == NotificationType.TOO_HIGH_SINGLE


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            TemperatureThresholds.SINGLE.value - 4,
            5 + TemperatureThresholds.AVERAGE.value,
        ),
        (-54, 200000000000000),
    ],
)
def test_average_temperature_too_high(example_temperature_reading):
    notification_event = Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == NotificationType.TOO_HIGH_AVERAGE


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            TemperatureThresholds.SINGLE.value - 1,
            TemperatureThresholds.SINGLE.value
            - 1
            - (
                TemperatureThresholds.SINGLE.value
                - TemperatureThresholds.SINGLE_INCREASE_DELTA.value
            ),
        ),
    ],
)
def test_increase_temperature_too_high(example_temperature_reading):
    notification_event = Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == NotificationType.RAPID_INCREASE


@pytest.mark.parametrize(
    "temp,average",
    [("alex", 45), ("alex", "sasg")],
)
def test_temperature_exception_handling(example_temperature_reading):
    with pytest.raises(TypeError):
        notification_event = Notifications(queued_notifications=[])
        res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
        print(f"res = {res}")
