#!/usr/bin/env python3
"""
Simple script: Run backfill and show before/after MongoDB stats.
"""

import os
import subprocess
import sys
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "capstone_d06")
COLL = os.getenv("MONGO_COLL", "readings")


def get_stats(coll):
    """Get database statistics."""
    total = coll.count_documents({})
    
    stats = {}
    for cow in ["cow1", "cow2", "cow3"]:
        count = coll.count_documents({"uuid": cow})
        stats[cow] = count
    
    return total, stats


def main():
    print("\n" + "="*70)
    print("SIMPLE BACKFILL TEST")
    print("="*70)
    
    # Connect
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        coll = client[DB][COLL]
    except Exception as e:
        print(f"✗ MongoDB error: {e}")
        return False
    
    # Choose mode
    import sys
    if len(sys.argv) > 1:
        mode = sys.argv[1]  # "current" or "realistic"
    else:
        mode = "current"
    
    script = f"backfill_{mode}.py" if mode != "current" else "backfill.py"
    days = 3
    
    print(f"\nMode: {mode.upper()}")
    print(f"Days: {days}")
    print(f"Script: {script}")
    
    # BEFORE
    print(f"\n[BEFORE]")
    before_total, before_stats = get_stats(coll)
    print(f"  Total docs: {before_total:,}")
    for cow in ["cow1", "cow2", "cow3"]:
        print(f"    {cow}: {before_stats[cow]:,}")
    
    if before_total > 0:
        print(f"\n  Clearing database...")
        coll.delete_many({})
        before_total, before_stats = get_stats(coll)
        print(f"  After clear: {before_total:,} documents")
    
    # RUN BACKFILL
    print(f"\n[RUNNING BACKFILL]")
    print(f"  $ python3 {script} --days {days}")
    
    try:
        result = subprocess.run(
            ["python3", script, "--days", str(days)],
            cwd=ROOT,
            capture_output=True,
            timeout=180,
            text=True
        )
        
        # Show output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"✗ Backfill failed (exit code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Timeout (backfill took too long)")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # AFTER
    print(f"\n[AFTER]")
    after_total, after_stats = get_stats(coll)
    print(f"  Total docs: {after_total:,}")
    for cow in ["cow1", "cow2", "cow3"]:
        print(f"    {cow}: {after_stats[cow]:,}")
    
    # STATS
    print(f"\n[STATISTICS]")
    inserted = after_total - before_total
    print(f"  Documents inserted: {inserted:,}")
    print(f"  Docs per cow: {inserted//3:,}")
    print(f"  Docs per cow per day: {inserted//9:,}")
    
    # Sample data
    print(f"\n[SAMPLE DATA]")
    sample = coll.find_one({"uuid": "cow1"}, sort=[("ts", -1)])
    if sample:
        print(f"  Latest document (cow1):")
        print(f"    ts: {sample['ts']}")
        print(f"    weight: {sample['weight']} kg")
        print(f"    temp: {sample['temp']}°C")
    
    first = coll.find_one({"uuid": "cow1"}, sort=[("ts", 1)])
    last = coll.find_one({"uuid": "cow1"}, sort=[("ts", -1)])
    if first and last:
        duration_hours = (last['ts'] - first['ts']).total_seconds() / 3600
        print(f"\n  Time span (cow1): {first['ts']} to {last['ts']}")
        print(f"  Duration: ~{duration_hours:.1f} hours")
    
    print(f"\n✓ Done!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
