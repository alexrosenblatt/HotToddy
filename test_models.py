import logging as test_logging

import pytest  # type: ignore
from deta import Deta  # type: ignore

from decouple import config  # type: ignore
import constants as c
import model as model

DETA_KEY = config("DETA_KEY")
deta = Deta(DETA_KEY)  # type: ignore


test_logging.basicConfig(
    filename="tests.log", encoding="utf-8", level=test_logging.DEBUG
)


temp_config = c.SensorConfig(sensor_type=c.SensorTypes(1))
humidity_config = c.SensorConfig(sensor_type=c.SensorTypes(2))
air_quality_config = c.SensorConfig(sensor_type=c.SensorTypes(3))


@pytest.fixture
def example_temperature_event() -> model.SensorLogEvent:
    temp = 95
    readings4 = model.SensorLogReading(
        sensor_name="arduino_1", sensor_reading=temp, sensor_type=c.SensorTypes(1)
    )
    readings5 = model.SensorLogReading(
        sensor_name="arduino_2", sensor_reading=temp, sensor_type=c.SensorTypes(2)
    )

    readings = model.SensorLogEvent(
        datetime=1665021239,
        event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
        best_lat=45.5728875,
        best_long=-122.66610937499999,
        readings=[readings4, readings5],
    )

    return readings


def test_event_parsing_2(example_temperature_event):
    parsed_response = example_temperature_event.parse_event()
    assert all(isinstance(i, model.ParsedReading) for i in parsed_response)
    for i in range(len(parsed_response)):
        assert parsed_response[i] == model.ParsedReading(
            datetime=example_temperature_event.datetime,
            event=example_temperature_event.event,
            best_lat=example_temperature_event.best_lat,
            best_long=example_temperature_event.best_long,
            sensor_name=example_temperature_event.readings[i].sensor_name,
            sensor_config=model.SensorConfig(
                example_temperature_event.readings[i].sensor_type
            ),
            sensor_reading=example_temperature_event.readings[i].sensor_reading,
            recent_average=example_temperature_event.compute_recent_sensor_averages(
                example_temperature_event.readings[i].sensor_name,
                example_temperature_event.readings[i].sensor_reading,
            ),
        )


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
            # temp reading is above threshold
            5 + temp_config.thresholds["single_reading"],
            # recent average is below the average alert threshold
            temp_config.thresholds["average"] - 5,
        ),
        # testing extremely large numbers
        (2000000000000000000, -5600000000),
        # testing decimals
        (1500.52323, -342.4),
    ],
)
def test_temperature_too_high(example_temperature_reading):
    notification_event = model.Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    test_logging.debug(f"res = {res}")
    assert res[1] == c.NotificationType.TOO_HIGH_SINGLE


@pytest.mark.parametrize(
    "temp,average",
    [
        (
            # single reading below threshold
            temp_config.thresholds["single_reading"] - 4,
            # average reading above threshold
            temp_config.thresholds["average"] + 5,
        ),
        # testing large numbers
        (-54, 200000000000000),
    ],
)
def test_average_temperature_too_high(example_temperature_reading):
    notification_event = model.Notifications(queued_notifications=[])
    res = notification_event._evaluate_for_notify_logic(example_temperature_reading)
    test_logging.debug(f"res = {res}")
    assert res[1] == c.NotificationType.TOO_HIGH_AVERAGE


@pytest.mark.skip(reason="feature disabled")
@pytest.mark.parametrize(
    "temp,average",
    [
        (
            # below single reading threshold
            temp_config.thresholds["single_reading"] - 1,
            # subtract single reading threshold from the increase change threshold + 1 to ensure that it detects when the temperature change happens fast enough
            temp_config.thresholds["single_reading"]
            - (temp_config.thresholds["single_increase_change"] + 1),
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


@pytest.mark.parametrize(
    "temp,average",
    [(90, 45)],
)
def test_database_error_handling(example_temperature_reading):
    test_db = deta.Base("test_db")
    db_res = example_temperature_reading.insert_parsed_reading_into_db(test_db)
    assert db_res == True
    res = test_db.fetch()
    for i in res.items:
        test_db.delete(i["key"])
