import os
import time
import random
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BROKER = os.getenv("BROKER")
TOPIC = os.getenv("TOPIC")
UID = os.getenv("UID")
LAT = float(os.getenv("LAT", -7.3))
LON = float(os.getenv("LON", 110.5))

FEED_TIMES = [8 * 3600, 14 * 3600]
INITIAL_FEED_WEIGHT = 30.0
BITE_RATE = (45, 48)
INTAKE_PER_BITE_DM = (0.45, 0.82)
DRY_MATTER_RATIO = 0.20

current_feed_weight = INITIAL_FEED_WEIGHT

def get_temperature():
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        return requests.get(url, timeout=5).json()["current_weather"]["temperature"]
    except:
        return 27.0

def get_intake_rate():
    bite_rate = random.uniform(*BITE_RATE)
    intake_dm = random.uniform(*INTAKE_PER_BITE_DM)
    dm_per_hour = (bite_rate * intake_dm / 1000) * 60
    return dm_per_hour / DRY_MATTER_RATIO

def simulate_feed(now, feed_weight):
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    detected = random.random() < 0.4

    if detected and feed_weight > 0:
        chewing_pause = random.random() < 0.2
        if not chewing_pause:
            intake_rate = get_intake_rate()
            efficiency = 0.5 + 0.5 * (feed_weight / INITIAL_FEED_WEIGHT)
            consumed = (intake_rate / 3600) * efficiency * random.uniform(0.8, 1.1)
            feed_weight = max(0, feed_weight - consumed)

    for feed_time in FEED_TIMES:
        if abs(seconds - feed_time) < 10:
            refill = random.uniform(5, 7)
            feed_weight = min(INITIAL_FEED_WEIGHT, feed_weight + refill)
            break

    return round(feed_weight, 3), detected

def publish_data(client, uid, temp, weight):
    payload = {"uid": uid, "temp": temp, "weight": weight}
    client.publish(TOPIC, json.dumps(payload))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] RFID detected → Published: {payload}")

def main():
    global current_feed_weight
    client = mqtt.Client()
    client.connect(BROKER, 1883, 60)
    print("Simulasi dimulai... Ctrl+C untuk berhenti.")
    try:
        while True:
            now = datetime.now()
            temp = get_temperature()
            current_feed_weight, detected = simulate_feed(now, current_feed_weight)
            if detected:
                publish_data(client, UID, temp, current_feed_weight)
            else:
                print(f"[{now.strftime('%H:%M:%S')}] Tidak ada sapi. Berat: {current_feed_weight:.2f} kg")
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()
        print("\nSimulasi dihentikan.")

if __name__ == "__main__":
    main()
