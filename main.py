import logging as logging

from fastapi import Form, Response
from twilio.twiml.messaging_response import MessagingResponse  # type: ignore

import model as m
from model import app
from constants import CacheConfig


# a POST route for webhook events to ingest readings, utilizes FastApi
@app.post("/")
def sensor_event(event: m.SensorLogEvent) -> m.SensorLogEvent:
    logging.debug(f"event triggered at {event.datetime}")
    # instantiates empty "queue" for notifications
    notification_event = m.Notifications(queued_notifications=[])

    parsed_readings = m.SensorLogEvent.parse_event(event)

    # inserts individual reading into a persistent database (all_readings_db) and a cache to support recent average calculation (recent_readings_db)
    for reading in parsed_readings:
        logging.debug(f"{reading} into db")
        insert_into_dbs(reading)
        notification_event.evaluate_for_notify(reading)

    # if any pending notifications are available, enqueues them to be sent
    if len(notification_event.get_notifications()) >= 0:
        if m.is_armed == True:
            notification_event.construct_twilio_sms()
    return event


def insert_into_dbs(reading):
    reading.insert_parsed_reading_into_db(
        database=m.all_readings_db,
    )
    reading.insert_parsed_reading_into_db(
        database=m.recent_readings_db,
        expiration_seconds=CacheConfig.EXPIRATION_TIME.value,
    )


@app.post("/activate/")
async def activate(Body: str = Form(...)):
    response = MessagingResponse()
    if (Body.lower()).rstrip() == "arm":
        return await m.set_arm_disarm_and_sms(response)
    elif (Body.lower()).rstrip() == "last temp":
        return await m.get_and_send_last_temp_reading(response)
    else:
        response.message(
            f"Nothing happened - 'Arm' to turn on alarm,'last' to get last reading."
        )
        return Response(content=str(response), media_type="application/xml")


# below is used for testing

readings1 = m.SensorLogReading(
    sensor_name="arduino_1", sensor_reading=10, sensor_type=m.SensorTypes(1)
)
readings2 = m.SensorLogReading(
    sensor_name="notecard", sensor_reading=10, sensor_type=m.SensorTypes(1)
)
readings3 = m.SensorLogReading(
    sensor_name="notecard2", sensor_reading=10, sensor_type=m.SensorTypes(1)
)

testevent = m.SensorLogEvent(
    datetime=1665021239,
    event="f3ec6e7b-382b-472b-ad13-c52d7327cf76",
    best_lat=45.5728875,
    best_long=-122.66610937499999,
    readings=[readings1, readings2, readings3],
)

sensor_event(testevent)
