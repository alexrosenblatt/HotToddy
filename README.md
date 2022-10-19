# HotToddy

## Description
Lightweight app for ingesting IOT sensor data (specifically from Blues Wireless hardware) and notifying via SMS. This was built with the intention of being agnostic to the sensor source and to easily scale as more sensors are added. At the moment, it's built specifically around the blues.io ecosystem for sensor ingestion and [Deta.Sh](deta.sh) for hosting and database management - but will eventually be generecized to easily scale to any source and hosting /database.

Within the hardware_src folder is source for the specific Arduino and Notecard interface this app was prototyped around. That source is heavily taken from this [Blues.io Tutorial](https://dev.blues.io/guides-and-tutorials/collecting-sensor-data/notecarrier-a/arduino-nano-33-ble-sense/c-cpp-arduino-wiring/)
 
 ## How It Works:
- Arduino parses data from temp sensor and adds it to queue on Blues.IO Cellular notecard. Let's call this sensor "Arduino1".
- Blues.IO Cellular notecard sends data from queue at a defined intervalto the Blues.io Notehub. The notehub is GUI for storing events and routing to various sources. In this case, a new event is parsed in the notehub using JSONata expression which extracts a set of fields from the event json serialized by Arduino1:
`{
    "datetime":when,
    "event":event,
    "best_lat":best_lat,
    "best_long":best_lon,
    "readings": body.readings
}`
  - Readings is a set of one or more sensor data from that specific event. If Arduino1 had ten sensors, there would be ten readings here.
- As events are sent to Notehub, they are parsed and routed to HotToddy's webhook. An example request body looks like: 
 
 ```
    "datetime": 1665342170,
    "event": "0ee55891-40b6-4167-97b8-2858364e71be",
    "best_lat": 45.5728875,
    "best_long": -122.66610937499999,
    "readings": [
        {
            "sensor_name": "notecard",
            "sensor_reading": 26.6875,
            "sensor_type": 1
        }
```
 
- Hot Toddy's API, built in FastAPI, validates this event and flattens the set of nested readings into a single Reading object.
- This objects attributes are stored in both a permanent database and a cache. This cache supports Hot Toddy's windowing of the latest readings to enable a notifications to be based on a recent average - this accounts for any sensor anomalies or unsteadiness. 
- Once flattened, each reading is evaluated for whether it should create a Notification. Notification thresholds are set via enums and specific to sensor types. The app is currently only configured for temperature sensing and notifying but extending this is relatively simple. 
- Once the Readings are evaluated, if any are flagged to notify, an SMS body is constructed and sent via twillio. 

## Currently under development!
