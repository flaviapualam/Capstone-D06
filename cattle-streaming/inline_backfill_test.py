#!/usr/bin/env python3
"""
Inline backfill test - no subprocess, direct execution.
"""

import os
import sys
import random
import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "capstone_d06")
COLL_NAME = os.getenv("MONGO_COLL", "readings")

# Current mode config
CURRENT_FEED = (5, 7)
CURRENT_RFID = (300, 600)
CURRENT_RATE = (0, 2)

# Realistic mode config
REALISTIC_FEED = (8, 12)
REALISTIC_RFID = (1200, 2400)
REALISTIC_RATE = (18, 24)


def generate_day_current(cow, date_utc):
    """Generate one day of data in CURRENT mode."""
    docs = []
    day_start_utc = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for feed_time_sec in [28800, 50400]:  # 08:00, 14:00
        jitter = random.randint(-600, 600)
        session_start = max(0, min(86400 - CURRENT_RFID[0], feed_time_sec + jitter))
        session_duration = random.randint(CURRENT_RFID[0], CURRENT_RFID[1])
        session_end = min(86400, session_start + session_duration)
        
        hopper = random.uniform(CURRENT_FEED[0], CURRENT_FEED[1])
        
        for sec_offset in range(session_start, session_end):
            rate = random.uniform(CURRENT_RATE[0], CURRENT_RATE[1])
            hopper = max(0, hopper - (rate / 3600.0))
            
            ts = day_start_utc + datetime.timedelta(seconds=sec_offset)
            docs.append({
                "ts": ts,
                "uuid": cow,
                "weight": round(hopper, 2),
                "temp": round(random.uniform(26.0, 30.0), 2)
            })
    
    return docs


def generate_day_realistic(cow, date_utc):
    """Generate one day of data in REALISTIC mode."""
    docs = []
    day_start_utc = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for feed_time_sec in [28800, 50400]:  # 08:00, 14:00
        jitter = random.randint(-300, 300)
        session_start = max(0, min(86400 - REALISTIC_RFID[0], feed_time_sec + jitter))
        session_duration = random.randint(REALISTIC_RFID[0], REALISTIC_RFID[1])
        session_end = min(86400, session_start + session_duration)
        
        hopper = random.uniform(REALISTIC_FEED[0], REALISTIC_FEED[1])
        rate_kg_per_min = random.uniform(REALISTIC_RATE[0], REALISTIC_RATE[1]) / 60.0
        rate_kg_per_sec = rate_kg_per_min / 60.0
        
        for sec_offset in range(session_start, session_end):
            hopper = max(0, hopper - rate_kg_per_sec)
            
            ts = day_start_utc + datetime.timedelta(seconds=sec_offset)
            docs.append({
                "ts": ts,
                "uuid": cow,
                "weight": round(hopper, 2),
                "temp": round(random.uniform(26.0, 30.0), 2)
            })
    
    return docs


def test_backfill(mode, days=3):
    """Test backfill insertion."""
    
    print(f"\n{'='*70}")
    print(f"Testing: {mode.upper()} mode ({days} days)")
    print(f"{'='*70}")
    
    # Connect
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        coll = client[DB][COLL_NAME]
    except Exception as e:
        print(f"✗ MongoDB error: {e}")
        return False
    
    # Clear
    print(f"\nClearing collection...")
    cleared = coll.delete_many({}).deleted_count
    print(f"  Cleared: {cleared:,} documents")
    
    # Generate
    print(f"\nGenerating data...")
    all_docs = []
    
    for cow_idx, cow in enumerate(["cow1", "cow2", "cow3"], 1):
        print(f"  [{cow_idx}/3] {cow}...", end=" ", flush=True)
        
        for day_offset in range(days):
            date_utc = datetime.datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - datetime.timedelta(days=day_offset)
            
            if mode == "current":
                docs = generate_day_current(cow, date_utc)
            else:
                docs = generate_day_realistic(cow, date_utc)
            
            all_docs.extend(docs)
        
        print(f"OK")
    
    # Insert
    print(f"\nInserting {len(all_docs):,} documents...")
    if all_docs:
        coll.insert_many(all_docs)
    
    # Verify
    total = coll.count_documents({})
    print(f"  Inserted: {total:,} documents")
    
    # Stats
    print(f"\nStatistics:")
    for cow in ["cow1", "cow2", "cow3"]:
        count = coll.count_documents({"uuid": cow})
        if count == 0:
            continue
        
        first = coll.find_one({"uuid": cow}, sort=[("ts", 1)])
        last = coll.find_one({"uuid": cow}, sort=[("ts", -1)])
        
        weights = list(coll.aggregate([
            {"$match": {"uuid": cow}},
            {"$group": {
                "_id": None,
                "min_w": {"$min": "$weight"},
                "max_w": {"$max": "$weight"},
                "avg_w": {"$avg": "$weight"}
            }}
        ]))[0]
        
        print(f"\n  {cow}:")
        print(f"    Docs: {count:,} (~{count//days:,}/day)")
        print(f"    Weight: {weights['min_w']:.2f} - {weights['max_w']:.2f} kg (avg {weights['avg_w']:.2f})")
        print(f"    Time: {first['ts'].strftime('%Y-%m-%d %H:%M:%S')} to {last['ts'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    return total


print("CATTLE STREAMING - BACKFILL COMPARISON")
print("="*70)

# Test both modes
current_count = test_backfill("current", days=3)
realistic_count = test_backfill("realistic", days=3)

# Summary
print(f"\n{'='*70}")
print("SUMMARY (3 days × 3 cows)")
print(f"{'='*70}")
print(f"  Current mode:    {current_count:,} documents")
print(f"  Realistic mode:  {realistic_count:,} documents")
if realistic_count > 0:
    ratio = current_count / realistic_count
    print(f"  Ratio (current/realistic): {ratio:.2f}x")
    print(f"\nInterpretation:")
    if ratio > 2:
        print(f"  • Current mode generates {ratio:.1f}x MORE documents")
        print(f"  • This is expected: many short sessions vs few long sessions")
    else:
        print(f"  • Similar document counts")

print(f"\n✓ Comparison complete!")
