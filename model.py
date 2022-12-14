import logging
import time
import datetime
from dataclasses import dataclass
from typing import List, Tuple

from decouple import config  # type: ignore
from deta import Deta  # type: ignore
from fastapi import FastAPI, Response
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore

logging.basicConfig(filename="models.log", encoding="utf-8", level=logging.DEBUG)


from constants import NotificationType, SensorTypes, SensorConfig, AlertTiming

TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN")
DETA_KEY = config("DETA_KEY")


TWILIO_CLIENT_IDS = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI()
deta = Deta(DETA_KEY)  # type: ignore

all_readings_db = deta.Base("therm-all-readings")
recent_readings_db = deta.Base("recent_readings")

last_averages: list[tuple[str, float]] = []

is_armed: bool = True


def _if_recent_reading() -> int:
    resp = recent_readings_db.fetch()
    for i in range(1, len(resp.items)):
        if resp.items[i]["datetime"] >= time.time() - AlertTiming.AVERAGE_ALERT_WINDOW:
            return True
    else:
        return False


async def set_arm_state():
    global is_armed
    if is_armed == True:
        is_armed = False
    else:
        is_armed = True
    return is_armed


async def get_and_send_last_temp_reading(response):
    all_readings_temp = all_readings_db.fetch(query={"sensor_type": 1})
    last_temp = max(all_readings_temp.items, key=lambda d: d["datetime"])
    last_temp_reading = last_temp["sensor_reading"]
    last_temp_datetime = datetime.datetime.fromtimestamp(last_temp["datetime"])
    try:
        response.message(
            f"Last temperature = {last_temp_reading}F at {last_temp_datetime} utc"
        )
        return Response(
            content=str(response),
            media_type="application/xml",
        )
    except:
        response.message(f"Last temp not available")
        return Response(
            content=str(response),
            media_type="application/xml",
        )


async def set_arm_disarm_and_sms(response):
    try:
        response.message(f"Alarm state set to {await set_arm_state()}")
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


@dataclass(repr=True)
class ParsedReading:
    """An individual reading from a single sensor parsed from SensorLogging event."""

    datetime: int
    event: str
    best_lat: float
    best_long: float
    sensor_name: str
    sensor_reading: float
    recent_average: float
    sensor_config: SensorConfig

    def insert_parsed_reading_into_db(self, database, expiration_seconds=0) -> bool:
        """Inserts into Deta.sh Database

        Args:
            database (str): Deta database to insert
            reading (Reading): Reading class associated with event to be stored
            expiration_seconds (int, optional): Number of seconds before result is purged. Defaults to 0.

        Returns:
            bool: Returns true if succesful, otherwise exception
        """
        try:
            db_response = database.put(
                self.parse_for_db_save(), expire_in=expiration_seconds
            )
            logging.debug(f"inserted {db_response} reading into {database}")
            return True
        except:
            logging.debug(f"failed to insert reading into {database}")
            raise MemoryError

    def parse_for_db_save(self):
        return {
            "datetime": self.datetime,
            "event": self.event,
            "best_lat": self.best_lat,
            "best_long": self.best_long,
            "sensor_name": self.sensor_name,
            "sensor_reading": self.sensor_reading,
            "recent_average": self.recent_average,
            "sensor_type": self.sensor_config.sensor_type,
        }


class SensorLogReading(BaseModel):
    """An individual capture from a single sensor contained within a single webhook event.
    Thrown away after parsing into an individual Reading object."""

    sensor_name: str
    sensor_reading: float
    sensor_type: SensorTypes


class SensorLogEvent(BaseModel):
    """Defines webhook event for ingestion by FastAPI. 'readings' is a list of captures from all sensors.  In the future, could be generecized."""

    datetime: int
    event: str
    best_lat: float
    best_long: float
    readings: List[SensorLogReading]

    def parse_event(self) -> list[ParsedReading]:
        """Deserializes SensorLogEvent into individual readings for storage.

        Args:
            sensor_log_event (SensorLogEvent): Event produced by / API call

        Returns:
            list:List of events split by individual sensor reading. If initial api call has 5 readings, this returns a list of 5
        """
        return [
            ParsedReading(
                datetime=self.datetime,
                event=self.event,
                best_lat=self.best_lat,
                best_long=self.best_long,
                sensor_name=r.sensor_name,
                sensor_config=SensorConfig(r.sensor_type),
                sensor_reading=r.sensor_reading,
                recent_average=self.compute_recent_sensor_averages(
                    r.sensor_name, r.sensor_reading
                ),
            )
            for r in self.readings
        ]

    def compute_recent_sensor_averages(
        self, sensor_name: str, sensor_reading: float
    ) -> float:
        """Hydrates recent_average field in notecard_event storage based off set of recent readings stored in cache.
        Set of readings in the average dependent on duration of expiration in recent_readings_db.


        Args:
            sensor_name (str): Name of sensor as specified in the reading field of the event
            sensor_reading (float): Sensor Reading passed in from Notebook event

        Returns:
            float: Computed average of readings per sensor
        """

        recent_readings = recent_readings_db.fetch().items
        last_readings = [
            reading["sensor_reading"]
            for reading in recent_readings
            if reading["sensor_name"] == sensor_name
        ]
        last_readings.append(sensor_reading)

        # average is a function of the time set for the recent_readings cache. To get a smaller window, set a smaller time for CacheConfig.ExpirationTime
        recent_sensor_average = sum(last_readings) / len(last_readings)
        last_averages.insert(0, (sensor_name, recent_sensor_average))
        return recent_sensor_average


@dataclass
class Notifications:
    """Handles evaluation for when to notify based on Reading state and mechanics for notification.
    Currently just twilio sms, could be extended to another service."""

    queued_notifications: List[tuple[ParsedReading, NotificationType]]

    def evaluate_for_notify(self, reading: ParsedReading) -> bool:
        """Wrapper for main notification evaluation logic - parses return from _evaluate_for_notify_logic and appends
        the reading to be sent.

        Args:
            reading (Reading): Reading to be evaluated

        Returns:
            bool: True if a reading has triggered a notification
        """
        notification_result = self._evaluate_for_notify_logic(reading)
        if notification_result[1] != NotificationType.NOOP:
            self.queued_notifications.append(notification_result)
            logging.debug(f"Appended {notification_result} to notification queue.")
            return True
        else:
            return False

    def construct_twilio_sms(self):
        """Parses queued notifications and constructs strings to include in SMS."""
        logging.debug(self.queued_notifications)

        if len(self.queued_notifications) >= 1:
            body: str = ""
            for notification in self.queued_notifications:
                if notification[0].sensor_config.sensor_type == 1:
                    message = f"Current temperature: {round(notification[0].recent_average,0)} F, Reason: {notification[1]} \n"
                    body = body.__add__(message)
                elif notification[0].sensor_config.sensor_type == 2:
                    message = f"Current humidity: {round(notification[0].recent_average,2)} %, Reason: {notification[1]} \n"
                    body = body.__add__(message)
            self.send_twilio_message(body)
        else:
            logging.debug("Not armed")

    def send_twilio_message(self, body: str):
        """Calls twilio API with constructed body string.

        Args:
            body (str): Parsed sensor readings from construct_twilio_sms()
        """
        TWILIO_CLIENT_IDS.messages.create(
            body=body,
            from_="+15405924574",
            to="+19739438803",
        )

    def get_notifications(self) -> List:
        """

        Returns:
            List: Notifications evaluated as meeting the threshold to send
        """
        return self.queued_notifications

    def _evaluate_for_notify_logic(
        self, parsed_reading: ParsedReading
    ) -> Tuple[ParsedReading, NotificationType]:
        """Main logic to evaluate if a notification needs to be sent based on the ingested sensor data.

        Args:
            reading (Reading): Current Reading object

        Returns:
            Tuple[Reading, NotificationType]: Returns the Reading object and the constant associated with the notification reason. Returns a NOOP if no notification is to be sent."
        """
        if (
            parsed_reading.recent_average
            >= parsed_reading.sensor_config.thresholds["average"]
        ):
            logging.debug(NotificationType.TOO_HIGH_AVERAGE)
            return parsed_reading, NotificationType.TOO_HIGH_AVERAGE

        # Evaluates if any current single reading is too high
        elif (
            parsed_reading.sensor_reading
            >= parsed_reading.sensor_config.thresholds["single_reading"]
        ):
            logging.debug(NotificationType.TOO_HIGH_SINGLE)
            return parsed_reading, NotificationType.TOO_HIGH_SINGLE

        # Evaluates if the last reading has increased too fast compared to the average
        elif (
            parsed_reading.sensor_reading - parsed_reading.recent_average
            >= parsed_reading.sensor_config.thresholds["single_increase_change"]
            and _if_recent_reading()  # TODO make this specific to the sensor_type
        ):

            logging.debug(NotificationType.RAPID_INCREASE)
            return parsed_reading, NotificationType.RAPID_INCREASE

        # # Evaluates if the last average has increased too fast compared to the previous average
        # elif (
        #     (
        #         (
        #             last_average[1] - parsed_reading.recent_average
        #             >= parsed_reading.sensor_config.thresholds[
        #                 "average_increase_change"
        #             ]
        #         )
        #         and _get_recent_readings() <= 5
        #     )
        #     for last_average in last_averages
        #     if last_average[0] == parsed_reading.sensor_name
        # ):

        #     logging.debug(NotificationType.RAPID_INCREASE_AVERAGE)
        #     return parsed_reading, NotificationType.RAPID_INCREASE_AVERAGE

        else:
            logging.debug("no notification triggered")
            return parsed_reading, NotificationType.NOOP
