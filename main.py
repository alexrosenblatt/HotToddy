from fastapi import Response, Form

from twilio.twiml.messaging_response import MessagingResponse  # type: ignore
from constants import CacheConfig, SensorConfig, SensorTypes
import model as m
import logging as logging

is_armed: bool = True

# a POST route for webhook events to ingest readings, utilizes FastApi
@m.app.post("/")
def sensor_event(event: m.SensorLogEvent) -> m.SensorLogEvent:
    logging.debug(f"event triggered at {event.datetime}")
    # instantiates empty "queue" for notifications
    notification_event = m.Notifications(queued_notifications=[])

    parsed_readings = m.SensorLogEvent.parse_event(event)

    # inserts individual reading into a persistent database (all_readings_db) and a cache to support recent average calculation (recent_readings_db)
    for reading in parsed_readings:
        logging.debug(f"{reading} into db")
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
        if is_armed == True:
            notification_event.construct_twilio_sms()
    return event


@m.app.post("/activate/")
async def activate(Body: str = Form(...)):
    if (Body.lower()).rstrip() == "arm":
        response = MessagingResponse()
        try:
            response.message(f"Current alarm armed state is {await set_arm_state()}")
            return Response(
                content=str(response),
                media_type="application/xml",
            )
        except:
            response.message(f"Arming Failed")
            return Response(
                content=str(response),
                media_type="application/xml",
            )

    else:
        response = MessagingResponse()
        response.message(f"Nothing happened")
        return Response(content=str(response), media_type="application/xml")


async def set_arm_state():
    global is_armed
    if is_armed == True:
        is_armed = False
    else:
        is_armed = True
    print(is_armed)
    return get_arm_state()


def get_arm_state():
    return is_armed


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
