#!/usr/bin/env python3
"""
===============================================================================
REALISTIC CATTLE FEEDING DATA SIMULATION — 3 COWS / 7 DAYS
===============================================================================

Generates two MongoDB collections for testing and training the Isolation Forest
anomaly detection model in a real-time cattle feed monitoring system.

COLLECTIONS:
    1. sensor_data  → raw time-series readings (IoT sensor simulation)
    2. metadata     → feeding session summaries with ground-truth labels

SYSTEM CONTEXT:
    Feeder nodes (STM32-based) read three sensors and publish to MQTT broker:
    • Load Cell: Feed container weight (every 5 seconds)
    • RFID Reader: Cow identity / presence (event-based)
    • Temperature: Shelter environment (every 60 seconds)

COWS AND DEVICES:
    | UID       | Sensor ID | Alias  |
    |-----------|-----------|--------|
    | 8H13CJ7   | 1         | COW_A  |
    | 7F41TR2   | 2         | COW_B  |
    | 9K22PQ9   | 3         | COW_C  |

    Each cow eats twice per day at 08:00 and 14:00 (±2 min jitter).
    Normal feeding lasts 60 ± 10 minutes.

GROUND-TRUTH HEALTH SCHEDULE:
    | UID       | Day(s) | Behavior              | sick_groundtruth |
    |-----------|--------|----------------------|------------------|
    | 8H13CJ7   | 3-5    | short_feed            | true             |
    | 7F41TR2   | 4      | no_show               | true             |
    | 9K22PQ9   | —      | idle_near_feeder/noise| false            |

USAGE:
    python backfill_realistic_v2.py \\
        --start-date 2025-10-28 \\
        --n-days 7 \\
        --seed 42 \\
        --batch-size 1000 \\
        --write-mongo
"""

import os
import sys
import json
import random
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Generator
from pymongo import MongoClient, errors
from pymongo.operations import InsertOne
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "capstone_d06")
MONGO_SENSOR_COLL = "sensor_data"
MONGO_METADATA_COLL = "metadata"

# Timezone offset (WIB = UTC+7)
TZ_OFFSET_MIN = int(os.getenv("TZ_OFFSET_MIN", "420"))

# ============================================================================
# COW DEFINITIONS
# ============================================================================

COWS = {
    "8H13CJ7": {"sensor_id": 1, "alias": "COW_A"},
    "7F41TR2": {"sensor_id": 2, "alias": "COW_B"},
    "9K22PQ9": {"sensor_id": 3, "alias": "COW_C"},
}

# Feeding times (seconds from midnight)
MORNING_SEC = 8 * 3600      # 08:00
AFTERNOON_SEC = 14 * 3600   # 14:00

# ============================================================================
# FEEDING PARAMETERS
# ============================================================================

# Normal session parameters (60 ± 10 minutes)
NORMAL_DURATION_MIN = 50     # minutes
NORMAL_DURATION_MAX = 70     # minutes

# Feed quantities (6.5-7.5 kg typical)
NORMAL_FEED_KG_MIN = 6.5
NORMAL_FEED_KG_MAX = 7.5

# Behavior-specific parameters
BEHAVIOR_PARAMS = {
    "normal": {
        "total_consumed_kg": (5.5, 7.0),        # 5.5-7 kg consumed
        "duration_min": (50, 70),               # 50-70 min session
        "uid_present": True,                    # RFID detected
    },
    "short_feed": {
        "total_consumed_kg": (1.0, 2.0),        # 1-2 kg (sick/weak)
        "duration_min": (10, 20),               # 10-20 min (stops early)
        "uid_present": True,                    # RFID detected
    },
    "no_show": {
        "total_consumed_kg": None,              # N/A: cow doesn't appear
        "duration_min": None,
        "uid_present": False,                   # No RFID detected
    },
    "idle_near_feeder": {
        "total_consumed_kg": (0.1, 0.3),        # <0.2 kg (lingering)
        "duration_min": (30, 60),               # 30-60 min (lingers)
        "uid_present": True,                    # RFID detected
    },
    "ghost_drop": {
        "total_consumed_kg": (2.0, 4.0),        # Moderate drop
        "duration_min": (20, 40),
        "uid_present": False,                   # No RFID (scale drift)
    },
    "sensor_noise": {
        "total_consumed_kg": (3.0, 5.0),
        "duration_min": (30, 50),
        "uid_present": True,                    # RFID present
    },
    "overeat": {
        "total_consumed_kg": (8.0, 10.0),       # >8 kg (dominance/calib)
        "duration_min": (60, 80),
        "uid_present": True,
    },
}

# Load cell noise characteristics
WEIGHT_NOISE_SIGMA = 0.03       # Gaussian noise σ=0.03 kg
WEIGHT_SPIKE_PROB = 0.005       # Occasional ±0.3 kg spikes (0.5%)
WEIGHT_SPIKE_MAGNITUDE = 0.3    # ±0.3 kg

# Temperature range (baseline 28-31°C, heat days 35-36°C)
TEMP_BASELINE_MIN = 28.0
TEMP_BASELINE_MAX = 31.0
TEMP_HEAT_MIN = 35.0
TEMP_HEAT_MAX = 36.0
TEMP_NOISE_RANGE = 0.5

# Sensor reading interval (5 seconds)
SENSOR_INTERVAL_SEC = 5

# ============================================================================
# GROUND-TRUTH HEALTH SCHEDULE
# ============================================================================

def get_health_schedule(uid: str, day: int, days_total: int) -> Tuple[str, bool]:
    """
    Determine behavior label and sick_groundtruth for a cow on a given day.

    Args:
        uid: Cow RFID UID
        day: Day offset (0 = start_date)
        days_total: Total simulation days

    Returns:
        (behavior_label, sick_groundtruth)
    """
    # COW_A (8H13CJ7): short_feed on days 3-5
    if uid == "8H13CJ7":
        if 2 <= day <= 4:  # days 3-5 (0-indexed)
            return "short_feed", True
        else:
            return "normal", False

    # COW_B (7F41TR2): no_show on day 4
    elif uid == "7F41TR2":
        if day == 3:  # day 4 (0-indexed)
            return "no_show", True
        else:
            return "normal", False

    # COW_C (9K22PQ9): idle_near_feeder and sensor_noise (healthy)
    else:  # 9K22PQ9
        if day % 2 == 0:  # alternate behaviors
            return "idle_near_feeder", False
        else:
            return "sensor_noise", False


# ============================================================================
# MATHEMATICAL MODELS
# ============================================================================

def generate_weight_curve(
    initial_kg: float,
    total_consumed_kg: float,
    duration_sec: int,
    alpha: Optional[float] = None,
    include_noise: bool = True,
    include_spikes: bool = True,
) -> Generator[float, None, None]:
    """
    Generate load cell weight curve over time using exponential decay.

    Mathematical model:
        f = (t / T)^alpha
        weight(t) = initial_kg - total_consumed_kg * f + N(0, σ)
        occasionally add ±0.3 kg spike (prob 0.005)

    Args:
        initial_kg: Starting weight
        total_consumed_kg: Total to consume
        duration_sec: Duration in seconds
        alpha: Shape parameter (default: random 0.9-1.2)
        include_noise: Add Gaussian noise
        include_spikes: Add random spikes

    Yields:
        Weight values for each 5-second interval
    """
    if alpha is None:
        alpha = random.uniform(0.9, 1.2)

    # Number of samples (5-second intervals)
    n_samples = duration_sec // SENSOR_INTERVAL_SEC

    for i in range(n_samples):
        # Normalized time progression [0, 1]
        t_norm = i / max(1, n_samples - 1)

        # Exponential decay curve
        f = t_norm ** alpha

        # Weight at this point
        weight = initial_kg - total_consumed_kg * f

        # Add Gaussian noise
        if include_noise:
            weight += random.gauss(0, WEIGHT_NOISE_SIGMA)

        # Add occasional spikes
        if include_spikes and random.random() < WEIGHT_SPIKE_PROB:
            weight += random.choice([-1, 1]) * WEIGHT_SPIKE_MAGNITUDE

        # Clamp to realistic range [0, initial_kg]
        weight = max(0, min(initial_kg, weight))

        yield weight


def generate_temperature_curve(
    duration_sec: int,
    is_heat_day: bool = False,
) -> Generator[float, None, None]:
    """
    Generate temperature readings over a session.

    Args:
        duration_sec: Session duration
        is_heat_day: True for heat stress (35-36°C)

    Yields:
        Temperature values for each 60-second interval
    """
    if is_heat_day:
        base_temp = random.uniform(TEMP_HEAT_MIN, TEMP_HEAT_MAX)
    else:
        base_temp = random.uniform(TEMP_BASELINE_MIN, TEMP_BASELINE_MAX)

    # Temperature samples every 60 seconds (not every 5-sec)
    n_samples = max(1, duration_sec // 60)

    for i in range(n_samples):
        # Slow drift over session
        drift = (i / max(1, n_samples - 1)) * 0.5 - 0.25
        temp = base_temp + drift + random.uniform(-TEMP_NOISE_RANGE, TEMP_NOISE_RANGE)
        yield max(20, min(40, temp))  # Clamp to realistic range


# ============================================================================
# FEEDING SESSION GENERATION
# ============================================================================

def generate_feeding_session(
    uid: str,
    date_utc: datetime.datetime,
    feeding_time_sec: int,
    behavior: str,
    sick_groundtruth: bool,
    sensor_id: int,
) -> Tuple[str, List[Dict], Dict]:
    """
    Generate a single feeding session (raw sensor data + metadata summary).

    Args:
        uid: Cow RFID UID (or None for ghost_drop)
        date_utc: Date of session (UTC)
        feeding_time_sec: Scheduled time (seconds from midnight)
        behavior: Behavior label
        sick_groundtruth: Ground truth health status
        sensor_id: Feeder device ID

    Returns:
        (session_id, sensor_docs_list, metadata_doc)
    """
    # Session scheduling with jitter (±2 min)
    jitter_sec = random.randint(-120, 120)
    session_start_sec = max(0, min(86400 - 300, feeding_time_sec + jitter_sec))
    session_end_sec = min(86400, session_start_sec + 86400)  # Cap at day boundary

    # Get behavior parameters
    params = BEHAVIOR_PARAMS[behavior]

    # Handle no_show (special case)
    if behavior == "no_show":
        session_id = f"{date_utc.strftime('%Y-%m-%d')}_{['PM' if feeding_time_sec > 43200 else 'AM'][0]}_{uid}"
        return session_id, [], {
            "session_id": session_id,
            "uid": uid,
            "sensor_id": sensor_id,
            "date": date_utc.strftime("%Y-%m-%d"),
            "feeding_time": "morning" if feeding_time_sec < 43200 else "afternoon",
            "behavior_label": behavior,
            "feed_consumed_kg": 0,
            "duration_min": 0,
            "temp_mean": 0,
            "sick_groundtruth": sick_groundtruth,
        }

    # Session duration and consumption
    duration_min_range = params["duration_min"]
    duration_min = random.randint(duration_min_range[0], duration_min_range[1])
    duration_sec = duration_min * 60

    # Initial hopper weight
    initial_weight_kg = random.uniform(NORMAL_FEED_KG_MIN, NORMAL_FEED_KG_MAX)

    # Total consumption
    consumed_range = params["total_consumed_kg"]
    total_consumed_kg = random.uniform(consumed_range[0], consumed_range[1])

    # Is this a heat day? (randomly ~20% of days)
    is_heat_day = random.random() < 0.2

    # Generate weight and temp curves
    weight_curve = list(generate_weight_curve(
        initial_weight_kg,
        total_consumed_kg,
        duration_sec,
    ))

    # Temperature samples (every 60 sec)
    temp_curve = list(generate_temperature_curve(duration_sec, is_heat_day))

    # Build sensor documents
    sensor_docs = []
    day_start_utc = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    for i, weight in enumerate(weight_curve):
        sec_in_day = session_start_sec + (i * SENSOR_INTERVAL_SEC)

        # Temperature (every 60 sec = every 12th sample)
        temp_idx = i // 12
        if temp_idx < len(temp_curve):
            temp = temp_curve[temp_idx]
        else:
            temp = temp_curve[-1] if temp_curve else 30.0

        # Timestamp
        ts_utc = day_start_utc + datetime.timedelta(seconds=sec_in_day)

        # Cow UID (None for ghost_drop)
        session_uid = uid if params["uid_present"] else None

        # Sensor document
        doc = {
            "timestamp": ts_utc,
            "uid": session_uid,
            "weight": round(weight, 2),
            "temp": round(temp, 1),
            "sensor_id": sensor_id,
        }
        sensor_docs.append(doc)

    # Session ID
    feeding_period = "morning" if feeding_time_sec < 43200 else "afternoon"
    session_id = f"{date_utc.strftime('%Y-%m-%d')}_{feeding_period}_{uid}"

    # Mean temperature
    temp_mean = sum(temp_curve) / len(temp_curve) if temp_curve else 30.0

    # Metadata document
    metadata_doc = {
        "session_id": session_id,
        "uid": uid,
        "sensor_id": sensor_id,
        "date": date_utc.strftime("%Y-%m-%d"),
        "feeding_time": feeding_period,
        "behavior_label": behavior,
        "feed_consumed_kg": round(total_consumed_kg, 2),
        "duration_min": duration_min,
        "temp_mean": round(temp_mean, 1),
        "sick_groundtruth": sick_groundtruth,
    }

    return session_id, sensor_docs, metadata_doc


# ============================================================================
# MAIN SIMULATION
# ============================================================================

def run_simulation(
    start_date: datetime.datetime,
    n_days: int,
    seed: Optional[int] = None,
    batch_size: int = 1000,
    write_mongo: bool = True,
    dry_run: bool = False,
) -> Dict:
    """
    Run the realistic cattle feeding simulation.

    Args:
        start_date: Start date (UTC)
        n_days: Number of days to simulate
        seed: Random seed for reproducibility
        batch_size: Batch size for MongoDB inserts
        write_mongo: Whether to write to MongoDB
        dry_run: If True, only generate data without inserting

    Returns:
        Dictionary with simulation statistics
    """
    if seed is not None:
        random.seed(seed)

    print("=" * 80)
    print("REALISTIC CATTLE FEEDING DATA SIMULATION — 3 COWS / 7 DAYS")
    print("=" * 80)

    # Configuration summary
    print(f"\n📋 CONFIGURATION:")
    print(f"   Start Date: {start_date.strftime('%Y-%m-%d')} (UTC)")
    print(f"   Days: {n_days}")
    print(f"   Seed: {seed if seed is not None else 'random'}")
    print(f"   MongoDB: {MONGO_URI} / {MONGO_DB}")
    print(f"   Write: {'Yes' if write_mongo else 'No (dry-run)'}")

    print(f"\n🐄 COWS:")
    for uid, info in COWS.items():
        print(f"   {info['alias']} ({uid}) - Sensor {info['sensor_id']}")

    print(f"\n📅 SCHEDULE:")
    print(f"   Morning: 08:00 (±2 min)")
    print(f"   Afternoon: 14:00 (±2 min)")
    print(f"   Normal duration: 50-70 min")
    print(f"   Feed per meal: 6.5-7.5 kg")

    print(f"\n⚠️  GROUND-TRUTH HEALTH SCHEDULE:")
    print(f"   COW_A (8H13CJ7): short_feed on days 3-5 (sick)")
    print(f"   COW_B (7F41TR2): no_show on day 4 (sick)")
    print(f"   COW_C (9K22PQ9): idle_near_feeder/sensor_noise (healthy)")

    # Connect to MongoDB (if write_mongo)
    if write_mongo:
        print(f"\n🔗 MONGODB:")
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info()
            db = client[MONGO_DB]
            sensor_coll = db[MONGO_SENSOR_COLL]
            metadata_coll = db[MONGO_METADATA_COLL]
            print(f"   ✓ Connected to {MONGO_DB}")
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            return {"success": False, "error": str(e)}

        # Clear collections
        print(f"\n🧹 CLEARING COLLECTIONS:")
        sensor_coll.delete_many({})
        metadata_coll.delete_many({})
        print(f"   ✓ Cleared {MONGO_SENSOR_COLL} and {MONGO_METADATA_COLL}")
    else:
        client = sensor_coll = metadata_coll = None

    # Generate simulation data
    print(f"\n⏳ GENERATING SIMULATION DATA:")

    total_sensor_docs = 0
    total_metadata_docs = 0
    sensor_batch = []
    metadata_batch = []

    # Iterate through each day
    for day_offset in range(n_days):
        date_utc = start_date + datetime.timedelta(days=day_offset)
        day_num = day_offset + 1

        print(f"\n   Day {day_num}/{n_days}: {date_utc.strftime('%Y-%m-%d')}")

        # Iterate through each cow
        for uid, cow_info in COWS.items():
            sensor_id = cow_info["sensor_id"]
            cow_alias = cow_info["alias"]

            # Morning and afternoon sessions
            for feed_time_sec in [MORNING_SEC, AFTERNOON_SEC]:
                period = "AM" if feed_time_sec == MORNING_SEC else "PM"

                # Determine behavior and health
                behavior, sick = get_health_schedule(uid, day_offset, n_days)

                # Generate session
                session_id, sensor_docs, metadata_doc = generate_feeding_session(
                    uid=uid,
                    date_utc=date_utc,
                    feeding_time_sec=feed_time_sec,
                    behavior=behavior,
                    sick_groundtruth=sick,
                    sensor_id=sensor_id,
                )

                # Track counts
                total_sensor_docs += len(sensor_docs)
                total_metadata_docs += 1

                # Add to batches
                sensor_batch.extend(sensor_docs)
                metadata_batch.append(metadata_doc)

                # Flush if batch is full
                if len(sensor_batch) >= batch_size:
                    if write_mongo and sensor_coll is not None:
                        try:
                            sensor_coll.insert_many(sensor_batch)
                        except Exception as e:
                            print(f"      ✗ Insert error: {e}")
                    sensor_batch = []

                if len(metadata_batch) >= batch_size:
                    if write_mongo and metadata_coll is not None:
                        try:
                            metadata_coll.insert_many(metadata_batch)
                        except Exception as e:
                            print(f"      ✗ Insert error: {e}")
                    metadata_batch = []

                # Log session summary
                print(
                    f"      {cow_alias} {period}: {behavior:20s} | "
                    f"consumed: {metadata_doc['feed_consumed_kg']:5.2f} kg | "
                    f"duration: {metadata_doc['duration_min']:3d} min | "
                    f"sick: {sick}"
                )

        print(f"      Total docs so far: {total_sensor_docs} sensor + {total_metadata_docs} metadata")

    # Final flush
    if sensor_batch and write_mongo and sensor_coll is not None:
        try:
            sensor_coll.insert_many(sensor_batch)
        except Exception as e:
            print(f"   ✗ Final sensor insert error: {e}")

    if metadata_batch and write_mongo and metadata_coll is not None:
        try:
            metadata_coll.insert_many(metadata_batch)
        except Exception as e:
            print(f"   ✗ Final metadata insert error: {e}")

    # Verification
    print(f"\n✅ VERIFICATION:")
    if write_mongo and sensor_coll is not None and metadata_coll is not None:
        sensor_count = sensor_coll.count_documents({})
        metadata_count = metadata_coll.count_documents({})
        print(f"   sensor_data collection: {sensor_count} documents")
        print(f"   metadata collection: {metadata_count} documents")

        # Per-cow breakdown
        print(f"\n   Per-cow breakdown:")
        for uid, cow_info in COWS.items():
            count = sensor_coll.count_documents({"uid": uid})
            metadata = metadata_coll.count_documents({"uid": uid})
            print(f"      {cow_info['alias']}: {count:6d} sensor docs, {metadata:2d} sessions")

        # Behavior distribution
        print(f"\n   Behavior distribution:")
        behaviors = metadata_coll.aggregate([
            {"$group": {"_id": "$behavior_label", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ])
        for doc in behaviors:
            print(f"      {doc['_id']:20s}: {doc['count']:3d} sessions")

        # Health stats
        sick_count = metadata_coll.count_documents({"sick_groundtruth": True})
        healthy_count = metadata_coll.count_documents({"sick_groundtruth": False})
        print(f"\n   Health stats:")
        print(f"      Sick sessions: {sick_count}")
        print(f"      Healthy sessions: {healthy_count}")

    # Summary
    print(f"\n{'=' * 80}")
    print(f"✓ SIMULATION COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nGenerated:")
    print(f"  • {total_sensor_docs:,} sensor readings (5-second intervals)")
    print(f"  • {total_metadata_docs} session summaries")
    print(f"  • {n_days} days × 2 meals/day × 3 cows = {n_days * 2 * 3} sessions total")

    print(f"\nData characteristics:")
    print(f"  ✓ Realistic weight curves (exponential decay)")
    print(f"  ✓ Gaussian noise (σ = {WEIGHT_NOISE_SIGMA} kg)")
    print(f"  ✓ Occasional spikes (±{WEIGHT_SPIKE_MAGNITUDE} kg, {WEIGHT_SPIKE_PROB*100}% prob)")
    print(f"  ✓ Temperature variations (baseline vs. heat days)")
    print(f"  ✓ Multiple behavior patterns (normal, short_feed, no_show, etc.)")
    print(f"  ✓ Ground-truth health labels for anomaly detection training")

    print(f"\nReady for:")
    print(f"  → Isolation Forest anomaly detection training")
    print(f"  → Real-time monitoring dashboard visualization")
    print(f"  → Model validation and testing")

    return {
        "success": True,
        "sensor_docs": total_sensor_docs,
        "metadata_docs": total_metadata_docs,
        "days": n_days,
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Realistic Cattle Feeding Data Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Default: 7 days from today
  python backfill_realistic_v2.py

  # Custom date range and seed
  python backfill_realistic_v2.py --start-date 2025-10-28 --n-days 7 --seed 42

  # Dry run (generate but don't write)
  python backfill_realistic_v2.py --dry-run

  # Custom batch size
  python backfill_realistic_v2.py --batch-size 5000

  # Full backfill with all options
  python backfill_realistic_v2.py \\
    --start-date 2025-10-28 \\
    --n-days 7 \\
    --seed 42 \\
    --batch-size 1000 \\
    --write-mongo
        """,
    )

    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        default=datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        - datetime.timedelta(days=7),
        help="Start date (YYYY-MM-DD), default: 7 days ago",
    )
    parser.add_argument(
        "--n-days",
        type=int,
        default=7,
        help="Number of days to simulate (default: 7)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: random)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for MongoDB inserts (default: 1000)",
    )
    parser.add_argument(
        "--write-mongo",
        action="store_true",
        default=True,
        help="Write to MongoDB (default: True)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate data but don't write to MongoDB",
    )

    args = parser.parse_args()

    # Run simulation
    result = run_simulation(
        start_date=args.start_date,
        n_days=args.n_days,
        seed=args.seed,
        batch_size=args.batch_size,
        write_mongo=not args.dry_run,
        dry_run=args.dry_run,
    )

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
