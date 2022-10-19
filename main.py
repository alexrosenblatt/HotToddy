from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from deta import Deta  # type: ignore
from fastapi import FastAPI
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore

from controller import *

# a POST route for webhook events to ingest readings
@app.post("/")
def webhook_handler(event: NotecardEvent) -> NotecardEvent:
    notification_event = Notification(queued_notifications=[])
    parsed_readings = NotecardEvent.parse_event(event)
    for reading in parsed_readings:
        reading.insert_reading_into_db(
            database=all_readings_db,
        )
        reading.insert_reading_into_db(
            database=recent_readings_db,
            expiration_seconds=360,
        )
        notification_event.evaluate_for_notify(reading)
    if len(notification_event.get_notifications()) >= 0:
        notification_event.send_notification()
    return event


readings1 = NotecardReading(
    sensor_name="arduino_1", sensor_reading=10, sensor_type=SensorType(1)
)
readings2 = NotecardReading(
    sensor_name="notecard", sensor_reading=10, sensor_type=SensorType(1)
)
readings3 = NotecardReading(
    sensor_name="notecard2", sensor_reading=10, sensor_type=SensorType(1)
)

testevent = NotecardEvent(
    datetime=1665021239,
    event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
    best_lat=45.5728875,
    best_long=-122.66610937499999,
    readings=[readings1, readings2, readings3],
)
# webhook_handler(testevent)
