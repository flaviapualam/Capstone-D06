import json, os, time, random, datetime
from pathlib import Path
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "cattle/sensor")

TICK_MS = int(os.getenv("TICK_MS", "1000"))
TZ_OFFSET_MIN = int(os.getenv("TZ_OFFSET_MIN", "0"))
MIN_FEED_KG = float(os.getenv("MIN_FEED_KG", "5"))
MAX_FEED_KG = float(os.getenv("MAX_FEED_KG", "7"))
CONSUMPTION_MAX_KG_PER_HR = float(os.getenv("CONSUMPTION_MAX_KG_PER_HR", "2"))
RFID_MIN_SEC = int(os.getenv("RFID_MIN_SEC", "120"))
RFID_MAX_SEC = int(os.getenv("RFID_MAX_SEC", "420"))
MORNING_SEC = int(os.getenv("MORNING_SEC", str(8*3600)))
AFTERNOON_SEC = int(os.getenv("AFTERNOON_SEC", str(14*3600)))

cows = json.loads((Path(__file__).with_name("cows.json")).read_text())

client = mqtt.Client(client_id="feeder-sim")
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

class TagState:
    def __init__(self):
        self.hopper = 0.0
        self.rfid_active = False
        self.rfid_until_ms = 0

state = { c["uuid"]: TagState() for c in cows }

def seconds_since_midnight_local():
    utc = datetime.datetime.utcnow()
    local = utc + datetime.timedelta(minutes=TZ_OFFSET_MIN)
    return local.hour*3600 + local.minute*60 + local.second

def maybe_drop_feed(tsm: int, st: TagState):
    if tsm in (MORNING_SEC, AFTERNOON_SEC):
        st.hopper += random.uniform(MIN_FEED_KG, MAX_FEED_KG)

def maybe_toggle_rfid(st: TagState):
    now_ms = int(time.time()*1000)
    if st.rfid_active:
        if now_ms >= st.rfid_until_ms or st.hopper <= 0:
            st.rfid_active = False
            st.rfid_until_ms = 0
    else:
        if st.hopper > 0 and random.random() < 0.15:
            st.rfid_active = True
            dur = random.uniform(RFID_MIN_SEC, RFID_MAX_SEC)
            st.rfid_until_ms = now_ms + int(dur*1000)

def ambient_temp():
    return round(random.uniform(26.0, 30.0), 2)

def tick():
    tsm = seconds_since_midnight_local()
    dt  = TICK_MS / 1000.0
    for cow in cows:
        uuid = cow["uuid"]
        st = state[uuid]

        maybe_drop_feed(tsm, st)
        maybe_toggle_rfid(st)

        if st.hopper > 0 and st.rfid_active:
            rate = random.uniform(0, CONSUMPTION_MAX_KG_PER_HR)
            eat  = min(rate/3600.0 * dt, st.hopper)
            st.hopper -= eat

            payload = {
                "uuid": uuid,
                "weight": round(st.hopper, 2),  # sisa pakan (kg)
                "temp": ambient_temp()
            }
            client.publish(MQTT_TOPIC, json.dumps(payload), qos=1, retain=True)

if __name__ == "__main__":
    print("feeder-sim running…")
    try:
        while True:
            tick()
            time.sleep(TICK_MS/1000.0)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
