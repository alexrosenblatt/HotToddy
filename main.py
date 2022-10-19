from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from deta import Deta  # type: ignore
from fastapi import FastAPI
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore

from models import *

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
