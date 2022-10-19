from dataclasses import dataclass
from typing import List, Tuple

from deta import Deta  # type: ignore
from fastapi import FastAPI
from pydantic import BaseModel
from twilio.rest import Client  # type: ignore

from decouple import config  # type: ignore

TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN")
DETA_KEY = config("DETA_KEY")


from constants import (
    TemperatureThresholds,
    HumidityThresholds,
    AirQualityThresholds,
    NotificationType,
    SensorType,
)

TWILIO_CLIENT_IDS = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI()
deta = deta = Deta(DETA_KEY)  # type: ignore

all_readings_db = deta.Base("therm-all-readings")
recent_readings_db = deta.Base("recent_readings")

last_averages: list[tuple[str, float]] = []


@dataclass(repr=True)
class Reading:
    """An individual reading from a single sensor parsed from Notecard event."""

    datetime: int
    event: str
    best_lat: float
    best_long: float
    sensor_name: str
    sensor_reading: float
    recent_average: float
    sensor_type: SensorType

    def insert_reading_into_db(self, database, expiration_seconds=0) -> bool:
        """Inserts into Deta.sh Database

        Args:
            database (str): Deta database to insert
            reading (Reading): Reading class associated with event to be stored
            expiration_seconds (int, optional): Number of seconds before result is purged. Defaults to 0.

        Returns:
            bool: Returns true if succesful, otherwise exception
        """
        try:
            database.put(self.__dict__, expire_in=expiration_seconds)
            return True
        except:
            return False


class NotecardReading(BaseModel):
    """An individual capture from a single sensor contained within a single webhook event. Thrown away after parsing into an individual Reading object."""

    sensor_name: str
    sensor_reading: float
    sensor_type: SensorType


class NotecardEvent(BaseModel):
    """Defines webhook event for FastAPI. readings is a list of captures from all sensors."""

    datetime: int
    event: str
    best_lat: float
    best_long: float
    readings: List[NotecardReading]

    def parse_event(self) -> list[Reading]:
        """Deserializes NotecardEvent into individual readings for storage.

        Args:
            notecard_event (NotecardEvent): Event produced by / API call

        Returns:
            list:List of events split by individual sensor reading. If initial api call has 5 readings, this returns a list of 5
        """
        return [
            Reading(
                datetime=self.datetime,
                event=self.event,
                best_lat=self.best_lat,
                best_long=self.best_long,
                sensor_name=r.sensor_name,
                sensor_type=r.sensor_type,
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
        recent_sensor_average = sum(last_readings) / len(last_readings[:6])
        last_averages.insert(0, (sensor_name, recent_sensor_average))
        return recent_sensor_average


@dataclass
class Notification:
    queued_notifications: List[tuple[Reading, NotificationType]]

    def evaluate_for_notify(self, reading: Reading) -> bool:
        res = self._evaluate_for_notify_logic(reading)
        if res[1] != NotificationType.NONE:
            self.queued_notifications.append(res)
            return True
        else:
            return False

    def send_notification(self):
        print(self.queued_notifications)
        if len(self.queued_notifications) >= 1:
            body: str = ""
            for qn in self.queued_notifications:
                message = (
                    f"{qn[0].sensor_name}, Reading: {qn[0].recent_average}, {qn[1]} \n"
                )
                body = body.__add__(message)
            self.send_twilio_message(body)

    def send_twilio_message(self, body):
        TWILIO_CLIENT_IDS.messages.create(
            body=body,
            from_="+15405924574",
            to="+19739438803",
        )

    def get_notifications(self) -> List:
        return self.queued_notifications

    def _evaluate_for_notify_logic(
        self,
        reading: Reading,
    ) -> Tuple[Reading, NotificationType]:

        if reading.sensor_type == SensorType.TEMPERATURE:
            threshold_type = TemperatureThresholds
        elif reading.sensor_type == SensorType.HUMIDITY:
            threshold_type = HumidityThresholds  # type: ignore
        elif reading.sensor_type == SensorType.AIRQUALITY:
            threshold_type = AirQualityThresholds  # type: ignore
        else:
            raise (ValueError)

        if reading.recent_average >= threshold_type.AVERAGE.value:
            print(NotificationType.TOO_HIGH_AVERAGE)
            return reading, NotificationType.TOO_HIGH_AVERAGE
        elif reading.sensor_reading >= threshold_type.SINGLE.value:
            print(NotificationType.TOO_HIGH_SINGLE)
            return reading, NotificationType.TOO_HIGH_SINGLE
        elif (
            reading.sensor_reading - reading.recent_average
            >= threshold_type.SINGLE_INCREASE_DELTA.value
        ):
            print(NotificationType.RAPID_INCREASE)
            return reading, NotificationType.RAPID_INCREASE
        elif (
            last_average[1] - reading.recent_average
            >= threshold_type.AVERAGE_INCREASE_DELTA.value
            for last_average in last_averages
            if last_average[0] == reading.sensor_name
        ):
            print(NotificationType.RAPID_INCREASE)
            return reading, NotificationType.RAPID_INCREASE
        else:
            print("no notification triggered")
            return reading, NotificationType.NONE
