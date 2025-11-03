#!/usr/bin/env python3
"""
Test script to verify the complete end-to-end flow:
1. Feeder-sim publishes to MQTT
2. Ingestor receives and inserts to MongoDB
3. Verify data in MongoDB
"""
import subprocess
import time
import sys
from pathlib import Path
import os
from pymongo import MongoClient
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "capstone_d06")
COLL = os.getenv("MONGO_COLL", "readings")

def test_flow():
    print("="*60)
    print("Testing Cattle Streaming End-to-End Flow")
    print("="*60)
    
    # Check MongoDB
    print("\n1. Connecting to MongoDB...")
    try:
        mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo.server_info()
        coll = mongo[DB][COLL]
        print(f"   ✓ Connected to {DB}.{COLL}")
    except Exception as e:
        print(f"   ✗ MongoDB connection failed: {e}")
        return False
    
    # Clear collection
    print("\n2. Clearing collection...")
    count_before = coll.count_documents({})
    coll.delete_many({})
    print(f"   ✓ Cleared {count_before} documents")
    
    # Start ingestor
    print("\n3. Starting ingestor...")
    ingestor_proc = subprocess.Popen(
        ["python3", "ingestor/ingestor.py"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    print("   ✓ Ingestor started")
    
    # Start feeder-sim
    print("\n4. Starting feeder-sim...")
    feeder_proc = subprocess.Popen(
        ["python3", "feeder-sim/feeder_sim.py"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    print("   ✓ Feeder-sim started")
    
    # Wait and check for data
    print("\n5. Waiting for data (10 seconds)...")
    for i in range(10):
        count = coll.count_documents({})
        print(f"   [{i+1}/10] Documents in MongoDB: {count}", end="\r")
        time.sleep(1)
    
    print("\n")
    count_after = coll.count_documents({})
    
    # Get recent data
    recent = list(coll.find().sort("ts", -1).limit(5))
    
    # Cleanup
    print("6. Cleaning up...")
    feeder_proc.terminate()
    ingestor_proc.terminate()
    feeder_proc.wait(timeout=5)
    ingestor_proc.wait(timeout=5)
    print("   ✓ Processes stopped")
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Documents inserted: {count_after}")
    if count_after > 0:
        print(f"\nLatest 5 documents:")
        for i, doc in enumerate(recent, 1):
            print(f"  {i}. {doc['uuid']}: weight={doc['weight']}kg, temp={doc['temp']}°C")
        print("\n✓ END-TO-END FLOW WORKING!")
        return True
    else:
        print("\n✗ No data received - check MQTT broker connection")
        return False

if __name__ == "__main__":
    success = test_flow()
    sys.exit(0 if success else 1)
