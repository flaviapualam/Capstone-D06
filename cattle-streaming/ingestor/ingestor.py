import os, json, datetime
from pathlib import Path
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "cattle/sensor")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB   = os.getenv("MONGO_DB", "capstone_d06")
COLL = os.getenv("MONGO_COLL", "readings")

mongo = MongoClient(MONGO_URI)
coll  = mongo[DB][COLL]

def on_connect(client, userdata, flags, rc, properties=None):
    print("ingestor connected:", rc)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())  # { uuid, weight, temp }
        doc = {
            "ts": datetime.datetime.utcnow(),  # timestamp dari server saat insert
            "uuid": data.get("uuid"),
            "weight": data.get("weight"),
            "temp": data.get("temp")
        }
        coll.insert_one(doc)
    except Exception as e:
        print("ingest error:", e)

if __name__ == "__main__":
    print("Mongo connected.")
    client = mqtt.Client(client_id="ingestor")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
