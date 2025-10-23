# app/services/mqtt_service.py
import asyncio
import json 
import paho.mqtt.client as mqtt
from app.core.config import settings
from datetime import datetime

async def save_to_mongo(data):
    from app.core.database import mongo_db
    try:
        if mongo_db is not None:
            await mongo_db.sensor_data.insert_one(data)
            print("Data saved to MongoDB")
        else: 
            print("MongoDB not connected")
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"✅ Connected to MQTT broker: {settings.MQTT_BROKER}")
        client.subscribe(settings.MQTT_TOPIC)
        print(f"📡 Subscribed to topic: {settings.MQTT_TOPIC}")
    else:
        print(f"❌ Failed to connect, reason code: {reason_code}")

def create_on_message(loop):
    def on_message(client, userdata, msg):
        try:
            print(f"📩 Message received on {msg.topic}. Payload type: {type(msg.payload)}")

            if isinstance(msg.payload, bytes):
                payload = json.loads(msg.payload.decode())
            else:
                print("❌ Payload is not in expected byte format.")
                return

            print(f"📩 Received on {msg.topic}: {payload}")

            document = {
                "sensor_id": payload.get("sensor_id"),
                "location": payload.get("location"),
                "temperature": payload.get("temperature"),
                "humidity": payload.get("humidity"),
                "timestamp": datetime.utcnow().isoformat(),
                "topic": msg.topic
            }

            # Jalankan coroutine di loop utama (thread-safe)
            asyncio.run_coroutine_threadsafe(save_to_mongo(document), loop)

        except Exception as e:
            print(f"❌ Error handling MQTT message: {e}")
    return on_message


def start_mqtt(loop):
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except Exception:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = create_on_message(loop)

    client.connect(settings.MQTT_BROKER, settings.MQTT_PORT)
    client.loop_start()
    print(f"🚀 MQTT client started on {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    return client