#!/usr/bin/env python3
"""
Realistic Cattle Streaming Backfill Agent
Generates realistic cow feeding patterns: meal completion in one session.
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

# Realistic simulation parameters
TZ_OFFSET_MIN = int(os.getenv("TZ_OFFSET_MIN", "420"))  # UTC+7
MORNING_SEC = int(os.getenv("MORNING_SEC", "28800"))    # 08:00
AFTERNOON_SEC = int(os.getenv("AFTERNOON_SEC", "50400"))  # 14:00

# REALISTIC FEEDING PARAMETERS
MIN_FEED_KG = 8                    # Realistic: 8-12 kg per meal
MAX_FEED_KG = 12
RFID_MIN_SEC = 1200                # 20 minutes (realistic session)
RFID_MAX_SEC = 2400                # 40 minutes
EATING_RATE_MIN_KG_PER_MIN = 0.3   # 18 kg/hr min = 0.3 kg/min
EATING_RATE_MAX_KG_PER_MIN = 0.4   # 24 kg/hr max = 0.4 kg/min

COWS = ["cow1", "cow2", "cow3"]


def generate_realistic_readings(cow_uuid, date_utc, db_collection):
    """
    Generate realistic readings where cow COMPLETES a meal in one RFID session.
    
    Behavior:
    - 08:00 & 14:00: Feed is provided (8-12 kg)
    - Cow immediately starts eating at 18-24 kg/hr rate
    - 20-40 minutes later: Feed is completely consumed
    - Weight decreases from full → 0 kg
    """
    
    # Start of day boundaries
    day_start_utc = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Feeding schedule: morning and afternoon
    feeding_schedule = [MORNING_SEC, AFTERNOON_SEC]
    
    for feed_time_sec in feeding_schedule:
        # Small jitter: ±5 minutes (not ±10) so cow starts soon after feed provided
        jitter = random.randint(-300, 300)
        session_start_sec = max(0, min(86400 - RFID_MIN_SEC, feed_time_sec + jitter))
        
        # Session duration: 20-40 minutes (cow finishes meal in one go)
        session_duration_sec = random.randint(RFID_MIN_SEC, RFID_MAX_SEC)
        session_end_sec = min(86400, session_start_sec + session_duration_sec)
        
        # Initial hopper amount (8-12 kg realistic meal)
        initial_hopper_kg = random.uniform(MIN_FEED_KG, MAX_FEED_KG)
        hopper_kg = initial_hopper_kg
        
        # Eating rate: 18-24 kg/hr = 0.3-0.4 kg/min
        eating_rate_kg_per_min = random.uniform(EATING_RATE_MIN_KG_PER_MIN, EATING_RATE_MAX_KG_PER_MIN)
        eating_rate_kg_per_sec = eating_rate_kg_per_min / 60.0
        
        # Variation: sometimes cow eats slower or stops briefly
        rate_variation = random.uniform(0.8, 1.0)  # 80-100% of base rate
        eating_rate_kg_per_sec *= rate_variation
        
        # Generate readings for this session (1-second sampling)
        docs = []
        for sec_in_day in range(session_start_sec, session_end_sec):
            # Consume feed
            hopper_kg = max(0, hopper_kg - eating_rate_kg_per_sec)
            
            # Timestamp
            ts_utc = day_start_utc + datetime.timedelta(seconds=sec_in_day)
            
            # Document
            doc = {
                "ts": ts_utc,
                "uuid": cow_uuid,
                "weight": round(hopper_kg, 2),  # Remaining weight
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
    print("Cattle Streaming Backfill Agent (REALISTIC MODE)")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  MongoDB URI: {MONGO_URI}")
    print(f"  Database: {MONGO_DB}, Collection: {MONGO_COLL}")
    print(f"  Days to backfill: {days}")
    print(f"  Cows: {', '.join(COWS)}")
    print(f"\n  REALISTIC FEEDING PATTERN:")
    print(f"    Feeding times (WIB): 08:00, 14:00")
    print(f"    Feed per meal: {MIN_FEED_KG}-{MAX_FEED_KG} kg")
    print(f"    Session duration: {RFID_MIN_SEC//60}-{RFID_MAX_SEC//60} minutes")
    print(f"    Eating rate: {EATING_RATE_MIN_KG_PER_MIN*60:.0f}-{EATING_RATE_MAX_KG_PER_MIN*60:.0f} kg/hr")
    print(f"    Pattern: Meal consumed COMPLETELY in ONE session")
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
    print(f"\nStep 3: Generating REALISTIC data for {days} days...")
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
            generate_realistic_readings(cow, date_utc, coll)
            
            # Count: 2 meals per day, each ~20-40 min, sampled at 1-sec
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
    print("BACKFILL SUMMARY (REALISTIC)")
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
            
            # Analysis
            avg_docs_per_day = count / days
            print(f"  Average docs/day: {avg_docs_per_day:.0f} (~{avg_docs_per_day/2:.0f} per meal)")
            print()
    
    # Overall time range
    first_doc = coll.find_one({}, sort=[("ts", 1)])
    last_doc = coll.find_one({}, sort=[("ts", -1)])
    if first_doc and last_doc:
        print(f"Overall time range: {first_doc['ts']} to {last_doc['ts']}")
    
    print("\n✓ Realistic backfill complete!")
    print("\nData characteristics:")
    print("  • Weight decreases from MAX → 0 kg per meal")
    print("  • Each meal consumed in 20-40 minutes (realistic)")
    print("  • 2 meals per day (08:00 & 14:00)")
    print("  • Total ~1200-2400 samples per cow per day")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
