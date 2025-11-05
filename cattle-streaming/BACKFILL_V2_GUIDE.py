#!/usr/bin/env python3
"""
Quick Reference: Realistic Cattle Feeding Data Simulation (backfill_realistic_v2.py)

This guide shows common usage patterns for generating training data with the
advanced simulator.
"""

# ============================================================================
# QUICK START EXAMPLES
# ============================================================================

"""
1. DEFAULT: 7 days of realistic data with disease patterns
   $ python backfill_realistic_v2.py
   
   → Generates from 7 days ago to today
   → Creates ~30,000 sensor readings + 42 sessions
   → COW_A sick days 3-5, COW_B no_show on day 4
   → Ready for immediate Isolation Forest training


2. REPRODUCIBLE DATASET (fixed seed for demos/testing)
   $ python backfill_realistic_v2.py --seed 42
   
   → Same exact data every time you run
   → Perfect for demos, testing, paper results
   → Results are reproducible across machines


3. CUSTOM DATE RANGE
   $ python backfill_realistic_v2.py --start-date 2025-10-01 --n-days 30
   
   → 30 days of data starting Oct 1
   → Larger dataset for more robust training
   → Still has disease patterns injected


4. DRY RUN (preview without writing)
   $ python backfill_realistic_v2.py --dry-run --seed 123
   
   → Generates data in memory only
   → Shows you the output before committing to DB
   → Fast preview (no MongoDB overhead)


5. HIGH-PERFORMANCE RUN
   $ python backfill_realistic_v2.py --batch-size 5000 --n-days 30
   
   → Faster MongoDB inserts (larger batches)
   → Good for large-scale backfills
   → Trade-off: more memory usage


6. CUSTOM SIMULATION
   $ python backfill_realistic_v2.py \\
       --start-date 2025-09-15 \\
       --n-days 60 \\
       --seed 999 \\
       --batch-size 2000 \\
       --write-mongo
   
   → 60 days of data from Sep 15
   → Fixed seed 999
   → Batch size 2000 for balance
   → Write to MongoDB
"""

# ============================================================================
# DATA SCHEMA REFERENCE
# ============================================================================

"""
SENSOR_DATA COLLECTION (raw time-series, ~30k docs per 7 days)
─────────────────────────────────────────────────────────────

{
    "_id": ObjectId("..."),
    "timestamp": ISODate("2025-10-30T08:12:35.000Z"),
    "uid": "8H13CJ7",          # Cow RFID UID (null for ghost_drop)
    "weight": 6.34,             # Feed container weight (kg)
    "temp": 30.2,               # Shelter temperature (°C)
    "sensor_id": 1              # Feeder device identifier
}

Characteristics:
  • 5-second sampling interval
  • Weight: realistic decay curve + noise + occasional spikes
  • Temperature: baseline + variations + heat days
  • uid: null for ghost_drop behavior (scale drift)


METADATA COLLECTION (session summaries, 42 docs per 7 days)
──────────────────────────────────────────────────────────

{
    "_id": ObjectId("..."),
    "session_id": "2025-10-30_morning_8H13CJ7",
    "uid": "8H13CJ7",           # Cow RFID UID
    "sensor_id": 1,             # Feeder device
    "date": "2025-10-30",
    "feeding_time": "morning",  # "morning" or "afternoon"
    "behavior_label": "normal", # See behavior table
    "feed_consumed_kg": 6.2,    # Total consumed
    "duration_min": 62,         # Session duration
    "temp_mean": 29.8,          # Average temperature
    "sick_groundtruth": false   # Ground-truth health label
}

Key field for anomaly detection: sick_groundtruth
  • true = anomaly (short_feed, no_show)
  • false = normal (including noise/idle patterns)
"""

# ============================================================================
# BEHAVIOR PATTERNS & ANOMALIES
# ============================================================================

"""
NORMAL PATTERNS (healthy, sick_groundtruth=false)
────────────────────────────────────────────────

Behavior: NORMAL
  Consumption: 5.5-7.0 kg (typical complete meal)
  Duration: 50-70 minutes (normal feeding time)
  Pattern: Smooth weight decay
  RFID: Present (uid detected)
  Use case: Baseline for anomaly detection

Behavior: IDLE_NEAR_FEEDER
  Consumption: 0.1-0.3 kg (lingers without eating much)
  Duration: 30-60 minutes (stays near feeder)
  Pattern: Minimal weight drop, stable
  RFID: Present (uid detected)
  Use case: Behavioral quirk (not necessarily sick)

Behavior: SENSOR_NOISE
  Consumption: 3-5 kg (normal range)
  Duration: 30-50 minutes
  Pattern: Erratic readings, noisy data
  RFID: Present
  Use case: Data cleaning validation

Behavior: GHOST_DROP
  Consumption: 2-4 kg
  Duration: 20-40 minutes
  Pattern: Weight drops but uid=null
  RFID: ABSENT (null) - scale drift or wrong tag
  Use case: Scale calibration validation


ANOMALY PATTERNS (sick/diseased, sick_groundtruth=true)
────────────────────────────────────────────────────────

Behavior: SHORT_FEED ⚠️
  Consumption: 1-2 kg (MUCH less than normal)
  Duration: 10-20 minutes (stops early, weak/sick)
  Pattern: Rapid weight drop then stop
  RFID: Present
  Interpretation: Signs of sickness, weakness, or disease
  → Primary indicator for Isolation Forest

Behavior: NO_SHOW ⚠️
  Consumption: 0 kg (doesn't appear)
  Duration: 0 minutes
  Pattern: No sensor data at all for session
  RFID: ABSENT (null)
  Interpretation: Cow missed feeding (separated, ill, hospitalized)
  → Strong anomaly indicator

Behavior: OVEREAT ⚠️ (optional, rare)
  Consumption: 8-10 kg (excessive)
  Duration: 60-80 minutes
  Pattern: Prolonged heavy feeding
  RFID: Present
  Interpretation: Calibration issue or dominance behavior
  → May or may not be sick (treated as normal for now)
"""

# ============================================================================
# GROUND-TRUTH INJECTION SCHEDULE
# ============================================================================

"""
The simulator injects disease patterns on specific days for validation:

7-DAY EXAMPLE (start-date 2025-10-28):
────────────────────────────────────────

Day 1 (2025-10-28): All cows normal
  └─ COW_A: normal (2 sessions)
  └─ COW_B: normal (2 sessions)
  └─ COW_C: idle_near_feeder (2 sessions)

Day 2 (2025-10-29): All cows normal
  └─ COW_A: normal (2 sessions)
  └─ COW_B: normal (2 sessions)
  └─ COW_C: sensor_noise (2 sessions) [alternates]

Day 3 (2025-10-30): COW_A sick ⚠️
  └─ COW_A: short_feed ⚠️ (2 sessions, sick=true)
  └─ COW_B: normal (2 sessions)
  └─ COW_C: idle_near_feeder (2 sessions)

Day 4 (2025-10-31): COW_A sick + COW_B no_show ⚠️
  └─ COW_A: short_feed ⚠️ (2 sessions, sick=true)
  └─ COW_B: no_show ⚠️ (2 sessions, sick=true)
  └─ COW_C: sensor_noise (2 sessions)

Day 5 (2025-11-01): COW_A still sick
  └─ COW_A: short_feed ⚠️ (2 sessions, sick=true)
  └─ COW_B: normal (2 sessions, recovery)
  └─ COW_C: idle_near_feeder (2 sessions)

Day 6-7: All cows normal (recovery period)

SUMMARY:
  ✓ COW_A: 3 days of disease (days 3-5, short_feed)
  ✓ COW_B: 1 day of disease (day 4, no_show)
  ✓ COW_C: Alternating healthy patterns (never sick)
  ✓ Total sick sessions: 8 out of 42 (19%)
  ✓ Class imbalance: typical for anomaly detection
"""

# ============================================================================
# ISOLATION FOREST TRAINING EXAMPLE
# ============================================================================

"""
Use the generated data for ML training:

    from pymongo import MongoClient
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client["capstone_d06"]
    
    # Load metadata (session summaries with labels)
    metadata = pd.DataFrame(list(db.metadata.find()))
    
    # Features for anomaly detection
    X = metadata[["feed_consumed_kg", "duration_min", "temp_mean"]].values
    y = metadata["sick_groundtruth"].values
    
    # Train Isolation Forest
    iso_forest = IsolationForest(contamination=0.2, random_state=42)
    iso_forest.fit(X)
    
    # Predictions
    predictions = iso_forest.predict(X)  # -1 = anomaly, 1 = normal
    
    # Evaluate
    from sklearn.metrics import classification_report
    print(classification_report(y, predictions < 0))
    
Expected results:
  • High recall on short_feed (small consumption + short duration)
  • High recall on no_show (zero consumption, zero duration)
  • Low false-positive rate on idle_near_feeder/sensor_noise
"""

# ============================================================================
# COMMON QUERIES
# ============================================================================

"""
MongoDB queries to explore the data:

1. All sick sessions
   db.metadata.find({"sick_groundtruth": true})
   
2. Sessions by behavior
   db.metadata.find({"behavior_label": "short_feed"})
   
3. COW_A data (all sessions)
   db.metadata.find({"uid": "8H13CJ7"})
   
4. Sensor readings for a specific session
   db.sensor_data.find({
       "timestamp": {
           "$gte": ISODate("2025-10-30T08:00:00Z"),
           "$lt": ISODate("2025-10-30T09:30:00Z")
       },
       "uid": "8H13CJ7"
   })
   
5. Count by behavior
   db.metadata.aggregate([
       {"$group": {"_id": "$behavior_label", "count": {"$sum": 1}}}
   ])
   
6. Average consumption by cow
   db.metadata.aggregate([
       {"$match": {"behavior_label": "normal"}},
       {"$group": {
           "_id": "$uid",
           "avg_consumed": {"$avg": "$feed_consumed_kg"}
       }}
   ])
"""

# ============================================================================
# PERFORMANCE & SCALING
# ============================================================================

"""
Typical performance metrics:

7-day run (default):
  • ~30,000 sensor readings
  • ~42 session summaries
  • Generation time: 5-10 seconds (dry-run)
  • MongoDB insert time: 10-30 seconds (depends on hardware)
  • Total: ~30-60 seconds

30-day run:
  • ~130,000 sensor readings
  • ~180 session summaries
  • Generation time: 20-40 seconds
  • MongoDB insert time: 30-120 seconds
  • Total: ~60-180 seconds

60-day run:
  • ~260,000 sensor readings
  • ~360 session summaries
  • Generation time: 40-80 seconds
  • MongoDB insert time: 60-240 seconds
  • Total: ~2-5 minutes

Performance tuning:
  • Use --batch-size 5000 for faster inserts on large datasets
  • Use --dry-run to benchmark without DB overhead
  • Use --seed for reproducible performance tests
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
Issue: "Connection failed: Server address lookup failed"
  → Check MongoDB is running: mongosh --eval "db.runCommand({ping: 1})"
  → Verify MONGO_URI in .env matches your setup

Issue: "pymongo not found"
  → Install: pip install pymongo python-dotenv

Issue: Script hangs during "GENERATING SIMULATION DATA"
  → Check MongoDB write performance
  → Try with --batch-size 500 to reduce memory usage
  → Use --dry-run first to isolate the issue

Issue: "No such file or directory: .env"
  → Create .env in cattle-streaming/ directory
  → See QUICK_START.md for example

Issue: Different random output each time
  → Use --seed <number> for reproducible results
  → Without --seed, each run is random
"""

# ============================================================================
# NEXT STEPS
# ============================================================================

"""
After generating data:

1. Train Isolation Forest
   → Use sick_groundtruth labels for validation
   → Split by date (days 1-5 train, days 6-7 test)

2. Real-time monitoring
   → Stream sensor_data to Flask/FastAPI endpoint
   → Apply trained model for live alerts

3. Dashboard visualization
   → Plot weight curves per session
   → Show behavior classifications
   → Highlight anomalies

4. Model refinement
   → Analyze false positives (idle_near_feeder misclassified as sick)
   → Tune contamination parameter
   → Add feature engineering (rate-of-change, velocity, etc.)

5. Scale to production
   → Use larger datasets (30-60 days)
   → Store models in MongoDB/S3
   → Deploy with FastAPI
"""

if __name__ == "__main__":
    print(__doc__)
