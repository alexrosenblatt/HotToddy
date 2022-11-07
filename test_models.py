import pytest  # type: ignore

import constants as c
import model as model

temp_config = c.SensorConfig(sensor_type=c.SensorTypes(1))
humidity_config = c.SensorConfig(sensor_type=c.SensorTypes(2))
air_quality_config = c.SensorConfig(sensor_type=c.SensorTypes(3))


@pytest.fixture
def example_temperature_event():
    temp = 95
    readings4 = model.SensorLogReading(
        sensor_name="arduino_1", sensor_reading=temp, sensor_type=c.SensorTypes(1)
    )

    readings = model.SensorLogEvent(
        datetime=1665021239,
        event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
        best_lat=45.5728875,
        best_long=-122.66610937499999,
        readings=[readings4],
    )

    return readings


@pytest.fixture
def example_temperature_reading(temp, average) -> model.ParsedReading:
    return model.ParsedReading(
        datetime=1665021239,
        event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
        best_lat=45.5728875,
        best_long=-122.66610937499999,
        sensor_name="arduino1",
        sensor_config=c.SensorConfig(c.SensorTypes(1)),
        sensor_reading=temp,
        recent_average=average,
    )


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            5 + temp_config.thresholds["single_reading"],
            temp_config.thresholds["average"] - 5,
        ),
        (2000000000000000000, -56),
    ],
)
def test_temperature_too_high(example_temperature_reading):
    notification_event = model.Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == c.NotificationType.TOO_HIGH_SINGLE


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            temp_config.thresholds["single_reading"] - 4,
            temp_config.thresholds["average"],
        ),
        (-54, 200000000000000),
    ],
)
def test_average_temperature_too_high(example_temperature_reading):
    notification_event = model.Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == c.NotificationType.TOO_HIGH_AVERAGE


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            temp_config.thresholds["single_reading"] - 1,
            temp_config.thresholds["single_reading"]
            - 1
            - (
                temp_config.thresholds["single_reading"]
                - temp_config.thresholds["single_increase_change"]
            ),
        ),
    ],
)
def test_increase_temperature_too_high(example_temperature_reading):
    notification_event = model.Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    print(f"res = {res}")
    assert res[1] == c.NotificationType.RAPID_INCREASE


@pytest.mark.parametrize(
    "temp,average",
    [("alex", 45), ("alex", "sasg")],
)
def test_temperature_exception_handling(example_temperature_reading):
    with pytest.raises(TypeError):
        notification_event = model.Notifications(queued_notifications=[])
        res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
        print(f"res = {res}")
