#!/usr/bin/env python3
"""
Realtime MQTT simulator for cattle feeding sessions
Continuous feeding simulator that publishes sensor data to MQTT broker.

- Simulates 3 devices with mapped RFID tags
- Publishes sensor data continuously with 30-min intervals between sessions
- Payload format: {"ip": "...", "id": "01", "rfid": "...", "w": 85.61, "temp": 84.89, "ts": "..."}

Usage:
  python3 main.py
"""

import time
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging

import paho.mqtt.client as mqtt
import numpy as np

# Hardcoded configuration
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_PREFIX = "cattle/sensor"

# Constants
DEVICE_IDS = ["1", "2", "3"]
RFID_MAPPING = {
    "1": "8H13CJ7",
    "2": "7F41TR2",
    "3": "9K22PQ9",
}
SHARED_IP = "10.18.236.88"
SAMPLING_RATE_SECONDS = 1

import os
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import numpy as np

# Load environment
load_dotenv()

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "cattle/sensor")
SESSION_LOG_FILE = os.getenv("SESSION_LOG_FILE", "session_metadata.jsonl")

# Constants (same as backfill_monthly_timescale.py)
DEVICE_IDS = ["1", "2", "3"]
RFID_MAPPING = {
    "1": "8H13CJ7",
    "2": "7F41TR2",
    "3": "9K22PQ9",
}
SHARED_IP = os.getenv("SIMULATOR_IP", "192.168.1.100")
SAMPLING_RATE_SECONDS = 1

# Feeding behavior parameters
NORMAL_FEEDING_DURATION_MIN = 60
FEEDING_DURATION_JITTER_MIN = 10
INTERVAL_BETWEEN_SESSIONS_MIN = 30  # Wait time between sessions
BUFFER_TIME_SECONDS = 60

# Load cell parameters
INITIAL_WEIGHT_MIN = 6.5
INITIAL_WEIGHT_MAX = 7.5
CONSUMPTION_RATE_MIN = 0.002
CONSUMPTION_RATE_MAX = 0.0025
WEIGHT_NOISE_STD = 0.005
SPIKE_PROBABILITY = 0.005
SPIKE_MAGNITUDE = 0.3

# Temperature parameters
TEMP_MIN = 28.0
TEMP_MAX = 31.0
TEMP_DRIFT_RATE = 0.02  # °C/min
TEMP_UPDATE_INTERVAL = 60  # seconds

# Session metadata output (optional logging)
SESSION_METADATA_DIR = "./session_metadata"
SESSION_METADATA_FILE = f"{SESSION_METADATA_DIR}/sessions.jsonl"

# Timezone for timestamps
TZ_OFFSET = timezone(timedelta(hours=7))  # WIB (GMT+7)



# ============================================================================
# MQTT CLIENT
# ============================================================================

class MQTTPublisher:
    """Handle MQTT connection and publishing"""
    
    def __init__(self, host: str, port: int):
        self.client = mqtt.Client()
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        self.client.on_connect = self._on_connect
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"✓ Connected to MQTT broker at {self.host}:{self.port}")
        else:
            self.logger.error(f"✗ Failed to connect to MQTT broker (code {rc})")
    
    def publish(self, topic: str, payload: dict):
        """Publish JSON payload to MQTT topic"""
        result = self.client.publish(topic, json.dumps(payload), qos=1)
        if not result.is_published():
            self.logger.warning(f"Failed to publish to {topic}")


# ============================================================================
# DEVICE SESSION SIMULATOR
# ============================================================================

class DeviceSessionSimulator:
    """Simulates a single feeding session for one device"""
    
    def __init__(self, device_id: str, session_start: datetime, duration_min: float):
        self.device_id = device_id
        self.rfid_id = RFID_MAPPING[device_id]
        self.session_start = session_start
        self.duration_min = duration_min
        self.session_end = session_start + timedelta(minutes=duration_min)
        
        # Initialize weight parameters
        self.initial_weight = random.uniform(INITIAL_WEIGHT_MIN, INITIAL_WEIGHT_MAX)
        self.consumption_rate = random.uniform(CONSUMPTION_RATE_MIN, CONSUMPTION_RATE_MAX)
        self.current_weight = self.initial_weight
        
        # Initialize temperature parameters
        self.current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
        self.temp_drift = random.uniform(-TEMP_DRIFT_RATE, TEMP_DRIFT_RATE)
        
        self.elapsed_seconds = 0
        self.readings_count = 0
        self.logger = logging.getLogger(__name__)

    
    def is_active(self, now: datetime) -> bool:
        """Check if session is currently active"""
        return self.session_start <= now < self.session_end
    
    def generate_reading(self, now: datetime) -> Optional[dict]:
        """Generate a single sensor reading for current timestamp"""
        if not self.is_active(now):
            return None
        
        # Calculate seconds from session start
        seconds_from_start = int((now - self.session_start).total_seconds())
        self.elapsed_seconds = seconds_from_start
        self.readings_count += 1
        
        # Update temperature every 60 seconds
        if seconds_from_start % TEMP_UPDATE_INTERVAL == 0:
            self.current_temp += self.temp_drift * (TEMP_UPDATE_INTERVAL / 60)
            self.current_temp = np.clip(self.current_temp, TEMP_MIN, TEMP_MAX)
        
        # Determine feeding phase
        duration_seconds = int(self.duration_min * 60)
        in_buffer_start = seconds_from_start < BUFFER_TIME_SECONDS
        in_buffer_end = seconds_from_start >= (duration_seconds - BUFFER_TIME_SECONDS)
        
        # Weight behavior
        if in_buffer_start or in_buffer_end:
            # Buffer phase: weight stays constant with small noise
            noise = np.random.normal(0, WEIGHT_NOISE_STD * 0.5)
            weight = self.current_weight + noise
        else:
            # Active feeding: decrease weight
            self.current_weight -= self.consumption_rate
            noise = np.random.normal(0, WEIGHT_NOISE_STD)
            
            # Random spike
            if random.random() < SPIKE_PROBABILITY:
                noise += random.choice([-1, 1]) * SPIKE_MAGNITUDE
            
            weight = self.current_weight + noise
        
        # Format payload with new structure
        # {"ip": "10.18.236.88", "id": "01", "rfid": "C96EF997", "w": 85.61, "temp": 84.89, "ts": "2000-01-01T07:04:07+07:00"}
        return {
            "ip": SHARED_IP,
            "id": self.device_id.zfill(2),  # "1" -> "01"
            "rfid": self.rfid_id,
            "w": round(max(0, weight), 2),
            "temp": round(self.current_temp, 2),
            "ts": now.astimezone(TZ_OFFSET).isoformat()
        }
    
    def get_metadata(self) -> dict:
        """Get session metadata for logging"""
        return {
            "device_id": self.device_id,
            "rfid_id": self.rfid_id,
            "session_start": self.session_start.isoformat(),
            "session_end": self.session_end.isoformat(),
            "duration_min": round(self.duration_min, 2),
            "initial_weight_kg": round(self.initial_weight, 3),
            "consumption_rate_kg_per_sec": round(self.consumption_rate, 6),
            "initial_temp_c": round(self.current_temp, 2),
            "temp_drift_c_per_min": round(self.temp_drift, 4),
            "total_readings": self.readings_count,
        }




# ============================================================================
# REALTIME SIMULATOR
# ============================================================================

class RealtimeSimulator:
    """Main simulator coordinating all devices"""
    
    def __init__(self, mqtt_host: str, mqtt_port: int, topic_prefix: str):
        self.mqtt = MQTTPublisher(mqtt_host, mqtt_port)
        self.topic_prefix = topic_prefix.rstrip("/")
        self.active_sessions: Dict[str, DeviceSessionSimulator] = {}
        self.next_session_time: Dict[str, datetime] = {}  # Track when each device can start next session
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Setup metadata logging
        import os
        os.makedirs(SESSION_METADATA_DIR, exist_ok=True)
        self.metadata_file = open(SESSION_METADATA_FILE, "a", encoding="utf-8")
        self.logger.info(f"Session metadata will be logged to: {SESSION_METADATA_FILE}")
        
        # Initialize all devices to start immediately
        for device_id in DEVICE_IDS:
            self.next_session_time[device_id] = datetime.now()

    
    def _start_new_session_if_ready(self, device_id: str, now: datetime):
        """Start a new session for device if it's ready and not currently active"""
        # Check if device already has an active session
        active_key = None
        for key, session in self.active_sessions.items():
            if session.device_id == device_id and session.is_active(now):
                active_key = key
                break
        
        if active_key:
            return  # Device is still in session
        
        # Check if enough time has passed since last session
        if now < self.next_session_time.get(device_id, now):
            return  # Not ready yet
        
        # Start new session
        duration = NORMAL_FEEDING_DURATION_MIN + random.uniform(
            -FEEDING_DURATION_JITTER_MIN, FEEDING_DURATION_JITTER_MIN
        )
        
        session = DeviceSessionSimulator(device_id, now, duration)
        session_key = f"{device_id}_{now.isoformat()}"
        self.active_sessions[session_key] = session
        
        # Schedule next session after this one ends + interval
        session_end = now + timedelta(minutes=duration)
        self.next_session_time[device_id] = session_end + timedelta(minutes=INTERVAL_BETWEEN_SESSIONS_MIN)
        
        self.logger.info(
            f"Started: Device {device_id} at {now.strftime('%H:%M:%S')} "
            f"for {duration:.1f} min (next session at {self.next_session_time[device_id].strftime('%H:%M:%S')})"
        )

    
    def _cleanup_old_sessions(self, now: datetime):
        """Remove sessions that have ended and log their metadata"""
        to_remove = [
            key for key, session in self.active_sessions.items()
            if session.session_end < now
        ]
        for key in to_remove:
            session = self.active_sessions[key]
            # Log session metadata to JSONL
            metadata = session.get_metadata()
            metadata["session_key"] = key
            metadata["completed_at"] = now.isoformat()
            
            self.metadata_file.write(json.dumps(metadata) + "\n")
            self.metadata_file.flush()
            
            self.logger.info(
                f"Session completed: Device {session.device_id} "
                f"({session.readings_count} readings, "
                f"{session.duration_min:.1f} min)"
            )
            
            del self.active_sessions[key]

    
    def run(self):
        """Main simulation loop"""
        self.running = True
        self.logger.info("=" * 80)
        self.logger.info("🐄 REALTIME CATTLE FEEDING SIMULATOR — CONTINUOUS MODE")
        self.logger.info("=" * 80)
        self.logger.info(f"Devices: {', '.join(DEVICE_IDS)}")
        self.logger.info(f"Session duration: ~{NORMAL_FEEDING_DURATION_MIN} min")
        self.logger.info(f"Interval between sessions: {INTERVAL_BETWEEN_SESSIONS_MIN} min")
        self.logger.info(f"MQTT broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        self.logger.info(f"Topic prefix: {self.topic_prefix}")
        self.logger.info("=" * 80)
        
        while self.running:
            try:
                now = datetime.now()
                
                # Try to start new sessions for each device if ready
                for device_id in DEVICE_IDS:
                    self._start_new_session_if_ready(device_id, now)
                
                # Generate and publish readings from active sessions
                for session in self.active_sessions.values():
                    if session.is_active(now):
                        reading = session.generate_reading(now)
                        if reading:
                            topic = f"{self.topic_prefix}/{reading['rfid']}"
                            self.mqtt.publish(topic, reading)
                
                # Cleanup old sessions
                self._cleanup_old_sessions(now)
                
                # Sleep until next second
                time.sleep(SAMPLING_RATE_SECONDS)

                
            except KeyboardInterrupt:
                self.logger.info("\n⚠ Interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)
        
        # Close metadata file on exit
        self.metadata_file.close()
        self.logger.info("✓ Simulator stopped")



# ============================================================================
# MAIN
# ============================================================================

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    
    # Create and run simulator
    simulator = RealtimeSimulator(
        mqtt_host=MQTT_BROKER_HOST,
        mqtt_port=MQTT_BROKER_PORT,
        topic_prefix=MQTT_TOPIC_PREFIX
    )
    
    simulator.run()
    return 0


if __name__ == "__main__":
    exit(main())

