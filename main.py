from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from deta import Deta  # type: ignore
from fastapi import FastAPI
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore
from constants import CacheConfig

from models import *

# a POST route for webhook events to ingest readings, utilizes FastApi
@app.post("/")
def webhook_handler(event: NotecardEvent) -> NotecardEvent:
    notification_event = Notification(queued_notifications=[])
    parsed_readings = NotecardEvent.parse_event(event)

    # inserts individual reading into a persistent database (all_readings_db) and a cache to support recent average calculation (recent_readings_db)
    for reading in parsed_readings:
        reading.insert_reading_into_db(
            database=all_readings_db,
        )
        reading.insert_reading_into_db(
            database=recent_readings_db,
            expiration_seconds=CacheConfig.EXPIRATION_TIME.value,
        )
        notification_event.evaluate_for_notify(reading)

    # if any pending notifications are available, enqueues them to be sent
    if len(notification_event.get_notifications()) >= 0:
        notification_event.send_notification()
    return event
