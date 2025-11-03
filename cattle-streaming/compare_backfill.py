#!/usr/bin/env python3
"""
Compare current vs realistic backfill data in MongoDB.
Shows statistics and patterns.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Load config
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "capstone_d06")
MONGO_COLL = os.getenv("MONGO_COLL", "readings")


def clear_db(coll):
    """Clear collection."""
    result = coll.delete_many({})
    return result.deleted_count


def run_backfill(script_name, days=3):
    """Run backfill script and return doc count."""
    print(f"\n  Running {script_name}...", end=" ", flush=True)
    try:
        result = subprocess.run(
            ["python3", script_name, "--days", str(days)],
            cwd=ROOT,
            capture_output=True,
            timeout=120,
            text=True
        )
        if result.returncode == 0:
            print("✓")
            return True
        else:
            print(f"✗ (exit code {result.returncode})")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ (timeout)")
        return False
    except Exception as e:
        print(f"✗ ({e})")
        return False


def analyze_data(coll, label):
    """Analyze and print data statistics."""
    
    print(f"\n{'='*70}")
    print(f"ANALYSIS: {label}")
    print(f"{'='*70}")
    
    total = coll.count_documents({})
    print(f"\nTotal documents: {total:,}")
    
    if total == 0:
        print("(empty)")
        return
    
    # Per cow
    print(f"\nPer cow:")
    for cow in ["cow1", "cow2", "cow3"]:
        count = coll.count_documents({"uuid": cow})
        if count == 0:
            continue
        
        first = coll.find_one({"uuid": cow}, sort=[("ts", 1)])
        last = coll.find_one({"uuid": cow}, sort=[("ts", -1)])
        
        # Min/max weight for this cow
        weight_stats = coll.aggregate([
            {"$match": {"uuid": cow}},
            {"$group": {
                "_id": None,
                "min_weight": {"$min": "$weight"},
                "max_weight": {"$max": "$weight"},
                "avg_weight": {"$avg": "$weight"}
            }}
        ])
        stats = list(weight_stats)[0]
        
        print(f"\n  {cow}:")
        print(f"    Documents: {count:,}")
        print(f"    Time range: {first['ts'].strftime('%Y-%m-%d %H:%M:%S')} to {last['ts'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Weight range: {stats['min_weight']:.2f} - {stats['max_weight']:.2f} kg")
        print(f"    Avg weight: {stats['avg_weight']:.2f} kg")
        print(f"    Docs per day: ~{count//3:,}")
    
    # Session analysis
    print(f"\n\nSession analysis:")
    
    # Get sample of weight drops (sessions)
    sample_docs = list(coll.aggregate([
        {"$group": {
            "_id": "$uuid",
            "docs": {"$push": {"ts": "$ts", "weight": "$weight"}},
            "count": {"$sum": 1}
        }},
        {"$limit": 1}
    ]))
    
    if sample_docs:
        cow_docs = sorted(sample_docs[0]["docs"], key=lambda x: x["ts"])
        
        # Look for weight drops (session starts)
        session_lengths = []
        prev_weight = -1
        session_start = None
        
        for doc in cow_docs[:500]:  # Sample first 500
            curr_weight = doc["weight"]
            
            # New session if weight increased (new feed)
            if curr_weight > prev_weight and prev_weight >= 0:
                if session_start is not None:
                    session_length = (doc["ts"] - session_start).total_seconds() / 60
                    session_lengths.append(session_length)
                session_start = doc["ts"]
            
            prev_weight = curr_weight
        
        if session_lengths:
            avg_session = sum(session_lengths) / len(session_lengths)
            max_session = max(session_lengths)
            min_session = min(session_lengths)
            print(f"  Session durations (sampled):")
            print(f"    Average: {avg_session:.1f} minutes")
            print(f"    Min: {min_session:.1f} minutes")
            print(f"    Max: {max_session:.1f} minutes")


def main():
    """Main comparison."""
    
    print("="*70)
    print("BACKFILL COMPARISON: CURRENT vs REALISTIC")
    print("="*70)
    
    # Connect
    print("\nConnecting to MongoDB...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        coll = client[MONGO_DB][MONGO_COLL]
        print("✓ Connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    # ===== CURRENT MODE =====
    print("\n" + "="*70)
    print("TEST 1: CURRENT MODE (backfill.py)")
    print("="*70)
    
    print("\nStep 1: Clear database")
    cleared = clear_db(coll)
    print(f"  Cleared: {cleared:,} documents")
    
    print("\nStep 2: Run current backfill (3 days)")
    if run_backfill("backfill.py", days=3):
        analyze_data(coll, "CURRENT MODE (5-7kg, 5-10min, 0-2kg/hr)")
    else:
        print("  Failed to run backfill")
        return False
    
    current_count = coll.count_documents({})
    
    # ===== REALISTIC MODE =====
    print("\n" + "="*70)
    print("TEST 2: REALISTIC MODE (backfill_realistic.py)")
    print("="*70)
    
    print("\nStep 1: Clear database")
    cleared = clear_db(coll)
    print(f"  Cleared: {cleared:,} documents")
    
    print("\nStep 2: Run realistic backfill (3 days)")
    if run_backfill("backfill_realistic.py", days=3):
        analyze_data(coll, "REALISTIC MODE (8-12kg, 20-40min, 18-24kg/hr)")
    else:
        print("  Failed to run backfill")
        return False
    
    realistic_count = coll.count_documents({})
    
    # ===== COMPARISON =====
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    print(f"\n3 days × 3 cows backfill:")
    print(f"  Current mode:    {current_count:,} documents")
    print(f"  Realistic mode:  {realistic_count:,} documents")
    print(f"  Ratio (Current/Realistic): {current_count/realistic_count:.1f}x")
    print(f"\nPer cow per day:")
    print(f"  Current:    ~{current_count//9:,} docs")
    print(f"  Realistic:  ~{realistic_count//9:,} docs")
    
    print(f"\n✓ Comparison complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
