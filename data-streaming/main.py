#!/usr/bin/env python3
"""
Realtime forward-fill MQTT simulator for feeding sessions (08:00 & 14:00 local)
- Reads DB to list farmers/cows
- CLI to activate/deactivate cows and set per-cow profile/duration
- Publishes per-second during real session windows to MQTT broker
- Payload matches `backfill_monthly_timescale.py` fields: timestamp, device_id, rfid_id, weight, temperature_c, ip

Usage (dev):
  python3 main.py --farmer-id <FARMER_ID>

Docker: use docker-compose.yml in same folder (see README)
"""

import os
import time
import json
import threading
import random
from datetime import datetime, date, time as dtime, timedelta
from typing import Dict, List, Optional

import psycopg2
import yaml
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load .env from current folder by default. You can instead point docker-compose to backend-fastapi-3/.env
load_dotenv()

POSTGRE_URI = os.getenv("POSTGRE_URI")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "cattle/sensor")

# Constants (kept similar to backfill_monthly_timescale.py)
SHARED_IP = os.getenv("SIMULATOR_IP", "192.168.1.100")
FEEDING_TIMES = ["08:00", "14:00"]  # Daily feeding schedule
SAMPLE_INTERVAL_SECONDS = 1
DEFAULT_SESSION_DURATION_MIN = 60

# Weight / temp defaults (can be overridden by profiles)
INITIAL_WEIGHT_MIN = 6.5
INITIAL_WEIGHT_MAX = 7.5
CONSUMPTION_RATE_MIN = 0.002
CONSUMPTION_RATE_MAX = 0.0025
WEIGHT_NOISE_STD = 0.005
SPIKE_PROBABILITY = 0.005
SPIKE_MAGNITUDE = 0.3

TEMP_MIN = 28.0
TEMP_MAX = 31.0
TEMP_DRIFT_RATE = 0.02  # °C/min
TEMP_UPDATE_INTERVAL = 60  # seconds

# Default mapping derived from backfill script
RFID_TO_DEVICE = {
    "8H13CJ7": "1",
    "7F41TR2": "2",
    "9K22PQ9": "3",
}

# Profiles file path
PROFILES_PATH = os.getenv("SIMULATOR_PROFILES", "session_profiles.yml")

# ----------------------- Helpers -----------------------

def load_profiles(path: str = PROFILES_PATH) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    cfg.setdefault("profiles", {})
    cfg.setdefault("overrides", {})
    return cfg


def hhmm_to_time(hhmm: str) -> dtime:
    h, m = map(int, hhmm.split(":"))
    return dtime(hour=h, minute=m, second=0)


def session_bounds_for_date(d: date, hhmm: str, duration_min: int) -> (datetime, datetime):
    start = datetime.combine(d, hhmm_to_time(hhmm))
    end = start + timedelta(minutes=duration_min)
    return start, end

# ----------------------- DB client -----------------------
class DBClient:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def fetch_farmers(self) -> List[Dict]:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT farmer_id, name FROM farmer ORDER BY name;")
                return [{"farmer_id": r[0], "name": r[1]} for r in cur.fetchall()]

    def fetch_cows_for_farmer(self, farmer_id: str) -> List[Dict]:
        q = """
        SELECT c.cow_id, c.name, ro.rfid_id
        FROM cow c
        LEFT JOIN rfid_ownership ro ON ro.cow_id = c.cow_id AND ro.time_end IS NULL
        WHERE c.farmer_id = %s
        ORDER BY c.name;
        """
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(q, (farmer_id,))
                rows = cur.fetchall()
                return [{"cow_id": str(r[0]), "name": r[1], "rfid": r[2]} for r in rows]

# ----------------------- MQTT writer -----------------------
class MQTTWriter:
    def __init__(self, host: str, port: int):
        self.client = mqtt.Client()
        self.host = host
        self.port = port
        self.client.on_connect = lambda cl, userdata, flags, rc: None
        # TODO: support username/password or TLS via env if needed (MQTT_USERNAME / MQTT_PASSWORD / MQTT_TLS_CA)
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict):
        self.client.publish(topic, json.dumps(payload), qos=1)

# ----------------------- Cow Simulator -----------------------
class CowSimulator:
    def __init__(self, cow: Dict, profiles_cfg: Dict = None):
        self.cow = cow
        self.active = False
        self.session_start: Optional[datetime] = None
        self.session_end: Optional[datetime] = None
        self.session_duration_min = DEFAULT_SESSION_DURATION_MIN
        self.profiles_cfg = profiles_cfg or {"profiles": {}, "overrides": {}}
        self.profile_name = self.profiles_cfg.get("overrides", {}).get(self.cow.get("cow_id"), "normal")
        self.reset_model_params()
        # runtime state
        self.current_weight = None
        self.current_temp = None
        self.temp_drift = None
        self.temp_update_counter = 0
        self.last_publish_ts: Optional[datetime] = None

    def reset_model_params(self):
        p = self.profiles_cfg.get("profiles", {}).get(self.profile_name, {})
        self.session_duration_min = int(p.get("duration_min", DEFAULT_SESSION_DURATION_MIN))
        self.duration_jitter_min = p.get("duration_jitter_min", 0)
        self.start_jitter_min = p.get("start_jitter_min", 0)
        self.consumption_min = p.get("consumption_rate_min", CONSUMPTION_RATE_MIN)
        self.consumption_max = p.get("consumption_rate_max", CONSUMPTION_RATE_MAX)
        self.weight_start_min = p.get("weight_start_min", INITIAL_WEIGHT_MIN)
        self.weight_start_max = p.get("weight_start_max", INITIAL_WEIGHT_MAX)
        self.spike_probability = p.get("spike_probability", SPIKE_PROBABILITY)
        self.spike_magnitude = p.get("spike_magnitude", SPIKE_MAGNITUDE)
        self.no_show_prob = p.get("no_show_prob", 0.0)
        self.include_gt = p.get("include_gt", False)

    def maybe_start_session(self, now: datetime):
        # keep session if already inside
        if self.session_start and self.session_start <= now < self.session_end:
            return
        # otherwise check scheduled windows for today
        for hh in FEEDING_TIMES:
            start, _ = session_bounds_for_date(now.date(), hh, self.session_duration_min)
            # apply per-cow start jitter (seconds)
            jitter = random.randint(-int(self.start_jitter_min * 60), int(self.start_jitter_min * 60))
            start = start + timedelta(seconds=jitter)
            # compute end with jitter
            end = start + timedelta(minutes=self.session_duration_min + random.uniform(-self.duration_jitter_min, self.duration_jitter_min))
            if start <= now < end:
                if random.random() < self.no_show_prob:
                    # no-show: do not set session (no publishes)
                    self.session_start = None
                    self.session_end = None
                    return
                # start session
                self.session_start = start
                self.session_end = end
                # initialize per-session state
                self.current_weight = random.uniform(self.weight_start_min, self.weight_start_max)
                self.consumption_rate = random.uniform(self.consumption_min, self.consumption_max)
                self.current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
                self.temp_drift = random.uniform(-TEMP_DRIFT_RATE, TEMP_DRIFT_RATE)
                self.temp_update_counter = 0
                self.last_publish_ts = None
                return
        # not in session
        self.session_start = None
        self.session_end = None
        self.last_publish_ts = None

    def should_publish(self, now: datetime) -> bool:
        if not self.active or not self.session_start:
            return False
        if self.last_publish_ts is None:
            return True
        return (now - self.last_publish_ts).total_seconds() >= SAMPLE_INTERVAL_SECONDS

    def generate_payload(self, now: datetime) -> dict:
        assert self.session_start and self.session_end
        # temp drift update
        self.temp_update_counter += 1
        if (self.temp_update_counter * SAMPLE_INTERVAL_SECONDS) % TEMP_UPDATE_INTERVAL == 0:
            self.current_temp += self.temp_drift * (TEMP_UPDATE_INTERVAL / 60.0)
            self.current_temp = max(TEMP_MIN, min(TEMP_MAX, self.current_temp))
        # consumption per second
        self.current_weight = max(0.0, self.current_weight - self.consumption_rate)
        noise = random.gauss(0, WEIGHT_NOISE_STD)
        if random.random() < self.spike_probability:
            noise += random.choice([-1, 1]) * self.spike_magnitude
        weight = max(0.0, self.current_weight + noise)
        rfid = self.cow.get("rfid")
        device_id = RFID_TO_DEVICE.get(rfid) if rfid else None
        payload = {
            "timestamp": now.isoformat(),
            "device_id": device_id,
            "rfid_id": rfid,
            "weight": round(weight, 3),
            "temperature_c": round(self.current_temp, 2),
            "ip": SHARED_IP,
        }
        # Note: do NOT include profile/ground-truth fields in the main payload to
        # keep the message schema compatible with backfill_monthly_timescale.py.
        # Ground-truth or labels should be sent to a separate topic or stored in DB
        # if needed. We intentionally avoid adding extra fields here.
        self.last_publish_ts = now
        return payload

# ----------------------- Simulator -----------------------
class ForwardRealtimeSimulator:
    def __init__(self, db_dsn: str, mqtt_host: str, mqtt_port: int, topic_prefix: str, profiles_path: str = PROFILES_PATH):
        self.db = DBClient(db_dsn)
        self.mqtt = MQTTWriter(mqtt_host, mqtt_port)
        self.topic_prefix = topic_prefix.rstrip("/")
        self.cow_sims: Dict[str, CowSimulator] = {}
        self.running = False
        self.lock = threading.Lock()
        self.profiles_path = profiles_path
        self.profiles_cfg = load_profiles(self.profiles_path)

    def load_cows_for_farmer(self, farmer_id: str):
        cows = self.db.fetch_cows_for_farmer(farmer_id)
        for c in cows:
            if c["cow_id"] not in self.cow_sims:
                self.cow_sims[c["cow_id"]] = CowSimulator(c, profiles_cfg=self.profiles_cfg)

    def activate_cow(self, cow_id: str):
        if cow_id in self.cow_sims:
            self.cow_sims[cow_id].active = True

    def deactivate_cow(self, cow_id: str):
        if cow_id in self.cow_sims:
            self.cow_sims[cow_id].active = False

    def set_profile(self, cow_id: str, profile_name: str) -> bool:
        sim = self.cow_sims.get(cow_id)
        if not sim:
            return False
        if profile_name not in self.profiles_cfg.get("profiles", {}):
            return False
        sim.profile_name = profile_name
        sim.reset_model_params()
        return True

    def set_duration(self, cow_id: str, minutes: int) -> bool:
        sim = self.cow_sims.get(cow_id)
        if not sim:
            return False
        sim.session_duration_min = minutes
        return True

    def reload_profiles(self):
        self.profiles_cfg = load_profiles(self.profiles_path)
        for sim in self.cow_sims.values():
            sim.profiles_cfg = self.profiles_cfg
            sim.profile_name = self.profiles_cfg.get("overrides", {}).get(sim.cow.get("cow_id"), sim.profile_name)
            sim.reset_model_params()

    def status(self):
        return {cid: {"active": sim.active, "name": sim.cow["name"], "profile": sim.profile_name} for cid, sim in self.cow_sims.items()}

    def run_loop(self):
        self.running = True
        while self.running:
            now = datetime.now()
            with self.lock:
                for cid, sim in self.cow_sims.items():
                    sim.maybe_start_session(now)
                    if sim.should_publish(now):
                        payload = sim.generate_payload(now)
                        topic = f"{self.topic_prefix}/{payload.get('rfid_id') or cid}"
                        self.mqtt.publish(topic, payload)
            time.sleep(0.2)

    def start(self):
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False

# ----------------------- CLI -----------------------

def interactive_cli(sim: ForwardRealtimeSimulator, farmer_id: str):
    print("Commands: list, activate <cow_id>, deactivate <cow_id>, status, set_profile <cow_id> <profile>, set_duration <cow_id> <minutes>, show_profiles, reload_profiles, quit")
    while True:
        try:
            parts = input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            sim.stop()
            break
        if not parts:
            continue
        cmd = parts[0]
        if cmd == "list":
            for cid, info in sim.status().items():
                print(f"{cid}: {info['name']} (active={info['active']}, profile={info['profile']})")
        elif cmd == "activate" and len(parts) >= 2:
            sim.activate_cow(parts[1]); print("ok")
        elif cmd == "deactivate" and len(parts) >= 2:
            sim.deactivate_cow(parts[1]); print("ok")
        elif cmd == "status":
            print(sim.status())
        elif cmd == "set_profile" and len(parts) == 3:
            ok = sim.set_profile(parts[1], parts[2]); print("ok" if ok else "failed")
        elif cmd == "set_duration" and len(parts) == 3:
            try:
                mins = int(parts[2])
            except ValueError:
                print("invalid minutes")
                continue
            ok = sim.set_duration(parts[1], mins); print("ok" if ok else "failed")
        elif cmd == "show_profiles":
            print("Profiles:\n", json.dumps(sim.profiles_cfg.get("profiles", {}), indent=2))
            print("Overrides:\n", json.dumps(sim.profiles_cfg.get("overrides", {}), indent=2))
        elif cmd == "reload_profiles":
            sim.reload_profiles(); print("reloaded")
        elif cmd == "quit":
            sim.stop(); break
        else:
            print("unknown command")

# ----------------------- Main -----------------------
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--farmer-id", help="farmer_id to load cows for", required=False)
    args = p.parse_args()

    if not POSTGRE_URI:
        raise RuntimeError("POSTGRE_URI missing in env")

    sim = ForwardRealtimeSimulator(POSTGRE_URI, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_PREFIX)

    farmer_id = args.farmer_id
    if not farmer_id:
        dbcli = DBClient(POSTGRE_URI)
        farmers = dbcli.fetch_farmers()
        print("Farmers:")
        for f in farmers:
            print(f"{f['farmer_id']} - {f['name']}")
        farmer_id = input("Enter farmer_id to simulate: ").strip()

    sim.load_cows_for_farmer(farmer_id)
    sim.start()
    print("Realtime simulator started. Activate cows to publish during 08:00 and 14:00 sessions.")
    interactive_cli(sim, farmer_id)
