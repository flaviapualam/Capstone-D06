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
SHARED_IP = "10.18.236.88"

# Constants
DEVICE_IDS = ["1", "2", "3"]
RFID_MAPPING = {
    "1": "A3B7E9F2",
    "2": "5D8C4A1E",
    "3": "F1G6H8K3",
}
SAMPLING_RATE_SECONDS = 1
# Feeding behavior parameters
NORMAL_FEEDING_DURATION_MIN = 60
FEEDING_DURATION_JITTER_MIN = 10
INTERVAL_BETWEEN_SESSIONS_MIN = 30  # Wait time between sessions
BUFFER_TIME_SECONDS = 60

# Load cell parameters (in GRAMS to match real sensor data)
INITIAL_WEIGHT_MIN_GRAMS = 5000   # 5 kg in grams
INITIAL_WEIGHT_MAX_GRAMS = 8000   # 8 kg in grams
CONSUMPTION_RATE_MIN_GRAMS = 1.5  # grams per second
CONSUMPTION_RATE_MAX_GRAMS = 3.5  # grams per second
WEIGHT_NOISE_STD_GRAMS = 500      # High noise (500g standard deviation)
SPIKE_PROBABILITY = 0.15          # 15% chance of spike (more frequent)
SPIKE_MAGNITUDE_GRAMS = 3000      # Large spikes up to 3kg
BURST_PROBABILITY = 0.05          # 5% chance of eating burst
BURST_DURATION_SECONDS = 10       # Burst lasts 10 seconds
BURST_MULTIPLIER = 5              # Consumption rate multiplied during burst

# Temperature parameters (matching real sensor: 26-31°C range)
TEMP_MIN = 26.0
TEMP_MAX = 31.0
TEMP_DRIFT_RATE = 0.15            # Faster temperature changes (°C/min)
TEMP_NOISE_STD = 0.5              # Temperature noise
TEMP_UPDATE_INTERVAL = 30         # Update every 30 seconds (more dynamic)

# Anomaly configuration
ANOMALY_PROBABILITY = 0.10        # 10% of sessions will have anomalies

# Distribution of anomaly types (must sum to 1.0)
ANOMALY_DISTRIBUTION = {
    'too_fast_eating': 0.20,       # 20% of anomalies - eating rate > 6 g/s
    'too_slow_eating': 0.20,       # 20% of anomalies - eating rate < 0.8 g/s
    'no_eating': 0.20,             # 20% of anomalies - consumption rate ~0
    'interrupted_session': 0.15,   # 15% of anomalies - session stops early
    'excessive_eating': 0.15,      # 15% of anomalies - session > 90 min
    'erratic_pattern': 0.10,       # 10% of anomalies - on-off eating pattern
}

# Anomaly-specific parameters
ANOMALY_FAST_CONSUMPTION_MIN = 6.0   # g/s (normal max: 3.5)
ANOMALY_FAST_CONSUMPTION_MAX = 10.0  # g/s
ANOMALY_SLOW_CONSUMPTION_MIN = 0.2   # g/s (normal min: 1.5)
ANOMALY_SLOW_CONSUMPTION_MAX = 0.8   # g/s
ANOMALY_EXCESSIVE_DURATION_MIN = 90  # minutes
ANOMALY_EXCESSIVE_DURATION_MAX = 120 # minutes
ANOMALY_INTERRUPTION_POINT_MIN = 0.3 # Interrupt at 30% of duration
ANOMALY_INTERRUPTION_POINT_MAX = 0.5 # Interrupt at 50% of duration
ANOMALY_ERRATIC_SWITCH_INTERVAL = 30 # Switch fast/slow every 30 seconds

# Session metadata output
SESSION_METADATA_DIR = "./session_metadata"
SESSION_METADATA_FILE = f"{SESSION_METADATA_DIR}/sessions.jsonl"

# Timezone for timestamps
TZ_OFFSET = timezone(timedelta(hours=7))  # WIB (GMT+7)


# ============================================================================
# MQTT CLIENT
# ============================================================================

class MQTTPublisher:
    """Handle MQTT connection and publishing"""
    
    def __init__(self):
        self.client = mqtt.Client()
        self.logger = logging.getLogger(__name__)
        self.connected = False
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        try:
            self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()
            
            # Wait for connection (max 5 seconds)
            wait_time = 0
            while not self.connected and wait_time < 5:
                time.sleep(0.1)
                wait_time += 0.1
            
            if not self.connected:
                self.logger.warning("⚠ MQTT connection timeout - will retry on publish")
                
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to MQTT broker: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.logger.info(f"✓ Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        else:
            self.connected = False
            self.logger.error(f"✗ Failed to connect to MQTT broker (code {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            self.logger.warning(f"⚠ Disconnected from MQTT broker (code {rc})")
    
    def publish(self, topic: str, payload: dict):
        """Publish JSON payload to MQTT topic"""
        if not self.connected:
            return  # Skip if not connected
        
        try:
            self.client.publish(topic, json.dumps(payload), qos=0)
        except Exception as e:
            self.logger.warning(f"Failed to publish: {e}")


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
        
        # Determine if this session is anomalous
        self.is_anomaly = random.random() < ANOMALY_PROBABILITY
        self.anomaly_type = None
        
        # Initialize weight parameters (in GRAMS)
        self.initial_weight = random.uniform(INITIAL_WEIGHT_MIN_GRAMS, INITIAL_WEIGHT_MAX_GRAMS)
        self.consumption_rate = random.uniform(CONSUMPTION_RATE_MIN_GRAMS, CONSUMPTION_RATE_MAX_GRAMS)
        self.current_weight = self.initial_weight
        
        # Initialize temperature parameters (ambient temperature)
        self.current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
        self.temp_drift = random.uniform(-TEMP_DRIFT_RATE, TEMP_DRIFT_RATE)
        
        # Burst eating state
        self.in_burst = False
        self.burst_end_time = None
        
        # Anomaly-specific attributes
        self.interruption_point = None
        self.erratic_phase = 0  # For erratic pattern
        self.session_interrupted = False
        
        # Apply anomaly behavior if this is an anomaly session
        if self.is_anomaly:
            self._apply_anomaly_behavior()
        
        self.elapsed_seconds = 0
        self.readings_count = 0
        self.logger = logging.getLogger(__name__)
    
    def _apply_anomaly_behavior(self):
        """Modify session parameters based on anomaly type"""
        # Select anomaly type based on distribution
        self.anomaly_type = random.choices(
            list(ANOMALY_DISTRIBUTION.keys()),
            weights=list(ANOMALY_DISTRIBUTION.values()),
            k=1
        )[0]
        
        if self.anomaly_type == 'too_fast_eating':
            # Very fast eating (stress, competition, hunger)
            self.consumption_rate = random.uniform(
                ANOMALY_FAST_CONSUMPTION_MIN, 
                ANOMALY_FAST_CONSUMPTION_MAX
            )
            self.logger.info(f"  ⚠️  ANOMALY: Too fast eating ({self.consumption_rate:.2f} g/s)")
            
        elif self.anomaly_type == 'too_slow_eating':
            # Very slow eating (illness, pain, weakness)
            self.consumption_rate = random.uniform(
                ANOMALY_SLOW_CONSUMPTION_MIN, 
                ANOMALY_SLOW_CONSUMPTION_MAX
            )
            self.logger.info(f"  ⚠️  ANOMALY: Too slow eating ({self.consumption_rate:.2f} g/s)")
            
        elif self.anomaly_type == 'no_eating':
            # No eating at all (sick, obstruction, feed problem)
            self.consumption_rate = 0.0
            self.logger.info(f"  ⚠️  ANOMALY: No eating (fake session)")
            
        elif self.anomaly_type == 'interrupted_session':
            # Session will stop early
            self.interruption_point = random.uniform(
                ANOMALY_INTERRUPTION_POINT_MIN, 
                ANOMALY_INTERRUPTION_POINT_MAX
            )
            interruption_min = self.duration_min * self.interruption_point
            self.logger.info(f"  ⚠️  ANOMALY: Interrupted session (will stop at {interruption_min:.1f} min)")
            
        elif self.anomaly_type == 'excessive_eating':
            # Extend duration significantly
            self.duration_min = random.uniform(
                ANOMALY_EXCESSIVE_DURATION_MIN, 
                ANOMALY_EXCESSIVE_DURATION_MAX
            )
            self.session_end = self.session_start + timedelta(minutes=self.duration_min)
            self.logger.info(f"  ⚠️  ANOMALY: Excessive eating ({self.duration_min:.1f} min)")
            
        elif self.anomaly_type == 'erratic_pattern':
            # On-off eating pattern
            self.logger.info(f"  ⚠️  ANOMALY: Erratic eating pattern (switching every {ANOMALY_ERRATIC_SWITCH_INTERVAL}s)")

    
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
        
        # Check for interrupted session anomaly
        if self.anomaly_type == 'interrupted_session' and not self.session_interrupted:
            if seconds_from_start >= (self.duration_min * 60 * self.interruption_point):
                # End session early
                self.session_end = now
                self.session_interrupted = True
                return None  # Stop generating readings
        
        # Update temperature every 30 seconds with noise
        if seconds_from_start % TEMP_UPDATE_INTERVAL == 0:
            self.current_temp += self.temp_drift * (TEMP_UPDATE_INTERVAL / 60)
            self.current_temp += np.random.normal(0, TEMP_NOISE_STD)
            self.current_temp = np.clip(self.current_temp, TEMP_MIN, TEMP_MAX)
        
        # Determine feeding phase
        duration_seconds = int(self.duration_min * 60)
        in_buffer_start = seconds_from_start < BUFFER_TIME_SECONDS
        in_buffer_end = seconds_from_start >= (duration_seconds - BUFFER_TIME_SECONDS)
        
        # Handle erratic pattern anomaly
        if self.anomaly_type == 'erratic_pattern':
            # Switch between fast and slow eating every N seconds
            phase = (seconds_from_start // ANOMALY_ERRATIC_SWITCH_INTERVAL) % 2
            if phase == 0:
                # Fast phase
                consumption = random.uniform(5.0, 7.0)
            else:
                # Slow/pause phase
                consumption = random.uniform(0.0, 0.5)
        else:
            # Normal consumption rate (or anomaly-modified rate)
            consumption = self.consumption_rate
        
        # Check for burst eating events (only for non-anomaly or non-erratic sessions)
        if not self.anomaly_type or self.anomaly_type not in ['erratic_pattern', 'no_eating']:
            if not self.in_burst and random.random() < BURST_PROBABILITY:
                self.in_burst = True
                self.burst_end_time = now + timedelta(seconds=BURST_DURATION_SECONDS)
            
            if self.in_burst and now >= self.burst_end_time:
                self.in_burst = False
        
        # Weight behavior with realistic noise patterns
        if in_buffer_start or in_buffer_end:
            # Buffer phase: weight stays constant with moderate noise
            noise = np.random.normal(0, WEIGHT_NOISE_STD_GRAMS * 0.3)
            weight = self.current_weight + noise
        else:
            # Active feeding: decrease weight with consumption rate
            
            # During burst: eat much faster (only if not anomaly)
            if self.in_burst and not self.anomaly_type:
                consumption *= BURST_MULTIPLIER
            
            self.current_weight -= consumption
            
            # Add realistic high-variance noise
            noise = np.random.normal(0, WEIGHT_NOISE_STD_GRAMS)
            
            # Random large spikes (simulating cow movement, sensor noise)
            if random.random() < SPIKE_PROBABILITY:
                spike = random.choice([-1, 1]) * random.uniform(SPIKE_MAGNITUDE_GRAMS * 0.5, SPIKE_MAGNITUDE_GRAMS)
                noise += spike
            
            weight = self.current_weight + noise
        
        # Ensure weight doesn't go negative
        weight = max(0, weight)
        
        # Format payload - weight in GRAMS to match real sensor
        # {"ip": "10.18.236.88", "id": "01", "rfid": "C96EF997", "w": 5432.18, "temp": 28.45, "ts": "2000-01-01T07:04:07+07:00"}
        return {
            "ip": SHARED_IP,
            "id": self.device_id.zfill(2),  # "1" -> "01"
            "rfid": self.rfid_id,
            "w": round(weight, 2),  # Weight in GRAMS (not kg)
            "temp": round(self.current_temp, 2),
            "ts": now.astimezone(TZ_OFFSET).isoformat()
        }
    
    def get_metadata(self) -> dict:
        """Get session metadata for logging"""
        metadata = {
            "device_id": self.device_id,
            "rfid_id": self.rfid_id,
            "session_start": self.session_start.isoformat(),
            "session_end": self.session_end.isoformat(),
            "duration_min": round(self.duration_min, 2),
            "initial_weight_grams": round(self.initial_weight, 2),
            "consumption_rate_grams_per_sec": round(self.consumption_rate, 3),
            "initial_temp_c": round(self.current_temp, 2),
            "temp_drift_c_per_min": round(self.temp_drift, 4),
            "total_readings": self.readings_count,
            "is_anomaly": self.is_anomaly,
            "anomaly_type": self.anomaly_type if self.is_anomaly else None,
        }
        
        # Add anomaly-specific metadata
        if self.anomaly_type == 'interrupted_session':
            metadata["interrupted"] = self.session_interrupted
            metadata["interruption_point"] = round(self.interruption_point, 3) if self.interruption_point else None
        
        return metadata




# ============================================================================
# REALTIME SIMULATOR
# ============================================================================

class RealtimeSimulator:
    """Main simulator coordinating all devices"""
    
    def __init__(self):
        self.mqtt = MQTTPublisher()
        self.topic_prefix = MQTT_TOPIC_PREFIX.rstrip("/")
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
                            self.mqtt.publish(self.topic_prefix, reading)
                
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
    simulator = RealtimeSimulator()
    simulator.run()
    return 0


if __name__ == "__main__":
    exit(main())

