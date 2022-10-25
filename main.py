from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from deta import Deta  # type: ignore
from fastapi import FastAPI
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore

from constants import CacheConfig
import models as m


# a POST route for webhook events to ingest readings, utilizes FastApi
@m.app.post("/")
def webhook_handler(event: m.NotecardEvent) -> m.NotecardEvent:
    notification_event = m.Notifications(queued_notifications=[])

    parsed_readings = m.NotecardEvent.parse_event(event)

    # inserts individual reading into a persistent database (all_readings_db) and a cache to support recent average calculation (recent_readings_db)
    for reading in parsed_readings:
        reading.insert_reading_into_db(
            database=m.all_readings_db,
        )
        reading.insert_reading_into_db(
            database=m.recent_readings_db,
            expiration_seconds=CacheConfig.EXPIRATION_TIME.value,
        )
        notification_event.evaluate_for_notify(reading)

    # if any pending notifications are available, enqueues them to be sent
    if len(notification_event.get_notifications()) >= 0:
        notification_event.construct_twilio_sms()
    return event


# For testing temperature

# readings1 = m.NotecardReading(
#     sensor_name="arduino_1", sensor_reading=10, sensor_type=m.SensorType(1)
# )

# readings3 = m.NotecardReading(
#     sensor_name="notecard2", sensor_reading=10, sensor_type=m.SensorType(2)
# )

# testevent = m.NotecardEvent(
#     datetime=1665021239,
#     event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
#     best_lat=45.5728875,
#     best_long=-122.66610937499999,
#     readings=[readings1],
# )
# webhook_handler(testevent)

# For testing humidity

# readings2 = m.NotecardReading(
#     sensor_name="notecard", sensor_reading=10, sensor_type=m.SensorType(2)
# )

# testevent_humidity = m.NotecardEvent(
#     datetime=1665021239,
#     event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
#     best_lat=45.5728875,
#     best_long=-122.66610937499999,
#     readings=[readings2],
# )

# webhook_handler(testevent_humidity)
