#include <Notecard.h>


#define usbSerial Serial
#define txRxPinsSerial Serial1

#define NOTE_PRODUCT_UID "com.gmail.rosenblatt.alex:temperature_tester"

int sensorPin = 0;
Notecard notecard;

void setup() {
  usbSerial.begin(115200);
  while (!usbSerial) {
  }


  usbSerial.println("Starting...");

  notecard.begin(txRxPinsSerial, 9600);
  notecard.setDebugOutputStream(usbSerial);

  notecard.debugSyncStatus(10000, 3);

  J *req = notecard.newRequest("hub.set");
  if (req != NULL) {
    JAddStringToObject(req, "product", NOTE_PRODUCT_UID);
    JAddStringToObject(req, "mode", "periodic");
    JAddNumberToObject(req, "outbound", 5);
    notecard.sendRequest(req);
  }
}



void loop() {

  //getting the voltage reading from the temperature sensor
  int reading = analogRead(sensorPin);

  // converting that reading to voltage, for 3.3v arduino use 3.3
  float voltage = reading * 3.3;
  voltage /= 1024.0;

  // print out the voltage
  Serial.print(voltage);
  Serial.println(" volts");

  // now print out the temperature
  float temperatureC = (voltage - 0.5) * 100;  //converting from 10 mv per degree with 500 mV offset
                                               //to degrees ((voltage - 500mV) times 100)
  Serial.print(temperatureC);
  Serial.println(" degrees C");

  // now convert to Fahrenheit
  float temperatureF = (temperatureC * 9.0 / 5.0) + 32.0;
  Serial.print(temperatureF);
  Serial.println(" degrees F");


  double cardtemperature = 0;
  J *rsp = notecard.requestAndResponse(notecard.newRequest("card.temp"));
  if (rsp != NULL) {
    cardtemperature = JGetNumber(rsp, "value");
    notecard.deleteResponse(rsp);
  }

  // Do the same to retrieve the voltage that is detected by the Notecard on its V+ pin.
  double cardvoltage = 0;
  rsp = notecard.requestAndResponse(notecard.newRequest("card.voltage"));
  if (rsp != NULL) {
    cardvoltage = JGetNumber(rsp, "value");
    notecard.deleteResponse(rsp);
  }


  J *req = notecard.newRequest("note.add");
  if (req != NULL) {
    JAddStringToObject(req, "file", "sensors.qo");
    if (temperatureF <= 90) {
      JAddBoolToObject(req, "sync", false);
    } else {
      JAddBoolToObject(req, "sync", true);
    }
    J *body = JAddObjectToObject(req, "body");
    if (body) {
      J *readings = JAddArrayToObject(body, "readings");
        J *sensor_1 = JAddObjectToObject(readings, "sensor_1");
        if (sensor_1) {
          JAddStringToObject(sensor_1, "sensor_name", "notecard");
          JAddNumberToObject(sensor_1, "sensor_reading", cardtemperature);
        }
        J *sensor_2 = JAddObjectToObject(readings, "sensor_2");
        if (sensor_2) {
          JAddStringToObject(sensor_2, "sensor_name", "arduino_1");
          JAddNumberToObject(sensor_2, "sensor_reading", temperatureF);
      }
    }
    notecard.sendRequest(req);
  }
  delay(120000); 
}