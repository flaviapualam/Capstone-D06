#!/usr/bin/env python3
"""
Cattle Streaming Backfill Agent
Generates historical mock data for 3 cows over N days and inserts to MongoDB.
"""

import os
import sys
import random
import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Load configuration
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "capstone_d06")
MONGO_COLL = os.getenv("MONGO_COLL", "readings")

# Simulation parameters
TZ_OFFSET_MIN = int(os.getenv("TZ_OFFSET_MIN", "420"))  # UTC+7
MORNING_SEC = int(os.getenv("MORNING_SEC", "28800"))    # 08:00
AFTERNOON_SEC = int(os.getenv("AFTERNOON_SEC", "50400"))  # 14:00
MIN_FEED_KG = float(os.getenv("MIN_FEED_KG", "5"))
MAX_FEED_KG = float(os.getenv("MAX_FEED_KG", "7"))
RFID_MIN_SEC = int(os.getenv("RFID_MIN_SEC", "300"))    # 5 min
RFID_MAX_SEC = int(os.getenv("RFID_MAX_SEC", "600"))    # 10 min
CONSUMPTION_MAX_KG_PER_HR = float(os.getenv("CONSUMPTION_MAX_KG_PER_HR", "2"))

COWS = ["cow1", "cow2", "cow3"]


def generate_readings(cow_uuid, date_utc, db_collection):
    """Generate readings for one cow on one day, insert to DB."""
    
    # Start of day boundaries
    day_start_utc = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Feeding schedule: morning and afternoon
    feeding_schedule = [MORNING_SEC, AFTERNOON_SEC]
    
    for feed_time_sec in feeding_schedule:
        # Random jitter: ±10 minutes (600 seconds)
        jitter = random.randint(-600, 600)
        session_start_sec = max(0, min(86400 - RFID_MIN_SEC, feed_time_sec + jitter))
        
        # Session duration: 5-10 minutes
        session_duration_sec = random.randint(RFID_MIN_SEC, RFID_MAX_SEC)
        session_end_sec = min(86400, session_start_sec + session_duration_sec)
        
        # Hopper amount at start of session
        hopper_kg = random.uniform(MIN_FEED_KG, MAX_FEED_KG)
        
        # Generate readings for this session (1-second sampling)
        docs = []
        for sec_in_day in range(session_start_sec, session_end_sec):
            # Eating rate: 0 to 2 kg/hr, converted to kg/sec
            eating_rate_kg_per_sec = random.uniform(0, CONSUMPTION_MAX_KG_PER_HR / 3600.0)
            hopper_kg = max(0, hopper_kg - eating_rate_kg_per_sec)
            
            # Timestamp
            ts_utc = day_start_utc + datetime.timedelta(seconds=sec_in_day)
            
            # Document
            doc = {
                "ts": ts_utc,
                "uuid": cow_uuid,
                "weight": round(hopper_kg, 2),
                "temp": round(random.uniform(26.0, 30.0), 2)
            }
            docs.append(doc)
        
        # Batch insert
        if docs:
            db_collection.insert_many(docs)


def main():
    """Main backfill function."""
    
    # Parse arguments
    days = 7
    clear_db = False
    
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    
    if "--clear" in sys.argv:
        clear_db = True
    
    print("=" * 70)
    print("Cattle Streaming Backfill Agent")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  MongoDB URI: {MONGO_URI}")
    print(f"  Database: {MONGO_DB}, Collection: {MONGO_COLL}")
    print(f"  Days to backfill: {days}")
    print(f"  Cows: {', '.join(COWS)}")
    print(f"  Feeding times (WIB): 08:00, 14:00")
    print(f"  RFID window: {RFID_MIN_SEC}-{RFID_MAX_SEC} seconds")
    print(f"  Consumption: 0-{CONSUMPTION_MAX_KG_PER_HR} kg/hr")
    print()
    
    # Connect to MongoDB
    print("Step 1: Connecting to MongoDB...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        coll = client[MONGO_DB][MONGO_COLL]
        print("        ✓ Connected successfully")
    except Exception as e:
        print(f"        ✗ Connection failed: {e}")
        return False
    
    # Optional: clear collection
    if clear_db:
        print("\nStep 2: Clearing collection...")
        result = coll.delete_many({})
        print(f"        ✓ Deleted {result.deleted_count} documents")
    else:
        print("\nStep 2: Skipping clear (use --clear to reset)")
    
    # Generate and insert data
    print(f"\nStep 3: Generating data for {days} days...")
    total_inserted = 0
    
    for cow_idx, cow in enumerate(COWS, 1):
        print(f"        [{cow_idx}/{len(COWS)}] {cow}...", end=" ", flush=True)
        cow_count = 0
        
        # Iterate through days (backwards from today)
        for day_offset in range(days):
            date_utc = datetime.datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - datetime.timedelta(days=day_offset)
            
            # Generate readings for this cow on this day
            generate_readings(cow, date_utc, coll)
            
            # Count inserted for this day (rough estimate)
            day_count = 2 * random.randint(RFID_MIN_SEC, RFID_MAX_SEC)
            cow_count += day_count
        
        total_inserted += cow_count
        print(f"~{cow_count} docs")
    
    # Verification
    print(f"\nStep 4: Verifying insertion...")
    actual_count = coll.count_documents({})
    print(f"        ✓ {actual_count} total documents in collection")
    
    # Summary report
    print("\n" + "=" * 70)
    print("BACKFILL SUMMARY")
    print("=" * 70)
    print(f"\nTotal documents: {actual_count}\n")
    
    for cow in COWS:
        count = coll.count_documents({"uuid": cow})
        if count > 0:
            first = coll.find_one({"uuid": cow}, sort=[("ts", 1)])
            last = coll.find_one({"uuid": cow}, sort=[("ts", -1)])
            print(f"{cow}:")
            print(f"  Documents: {count}")
            print(f"  First reading: {first['ts']}")
            print(f"  Last reading: {last['ts']}")
            print()
    
    # Overall time range
    first_doc = coll.find_one({}, sort=[("ts", 1)])
    last_doc = coll.find_one({}, sort=[("ts", -1)])
    if first_doc and last_doc:
        print(f"Overall time range: {first_doc['ts']} to {last_doc['ts']}")
    
    print("\n✓ Backfill complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
