# Cattle Streaming Backfill Agent

Generate historical mock data for the cattle-streaming system without using MQTT.

## 🎯 Quick Choice

### Use `backfill.py` (Default)
For **MQTT flow testing & load testing**
- Feed: 5–7 kg, Sessions: 5–10 min, Rate: 0–2 kg/hr
- High message frequency (good for testing)
- Many short RFID sessions (~20 per meal)

### Use `backfill_realistic.py` (Realistic)
For **Analytics & production-like data**
- Feed: 8–12 kg, Sessions: 20–40 min, Rate: 18–24 kg/hr
- Realistic cow feeding (meal completes in one session)
- Lower message volume (realistic)

See [`FEEDING_COMPARISON.md`](./FEEDING_COMPARISON.md) for detailed comparison.

## Overview

The backfill agents create synthetic time-series data for 3 cows (cow1, cow2, cow3) over N days, directly inserting into MongoDB.

### Default Mode (`backfill.py`)
- **Feeding pulses**: 08:00 & 14:00 WIB daily (5–7 kg feed per pulse)
- **RFID sessions**: 5–10 minute windows (±10 min jitter)
- **Consumption**: 0–2 kg/hr during sessions
- **Use case**: Testing MQTT flow, load testing

### Realistic Mode (`backfill_realistic.py`)
- **Feeding pulses**: 08:00 & 14:00 WIB daily (8–12 kg feed per pulse)
- **RFID sessions**: 20–40 minute windows (realistic meal duration)
- **Consumption**: 18–24 kg/hr during sessions (realistic eating rate)
- **Use case**: Analytics, production-like data

## Usage

```bash
# Generate 7 days (DEFAULT - high frequency)
python3 backfill.py

# Generate 14 days and clear existing data
python3 backfill.py --days 14 --clear

# Generate 30 days
python3 backfill.py --days 30

# === REALISTIC MODE ===

# Generate 7 days (REALISTIC pattern)
python3 backfill_realistic.py

# Generate 14 days and clear
python3 backfill_realistic.py --days 14 --clear
```

## Output Example

```
======================================================================
Cattle Streaming Backfill Agent
======================================================================

Configuration:
  MongoDB URI: mongodb://localhost:27017
  Database: capstone_d06, Collection: readings
  Days to backfill: 7
  Cows: cow1, cow2, cow3
  Feeding times (WIB): 08:00, 14:00
  RFID window: 300-600 seconds
  Consumption: 0-2 kg/hr

Step 1: Connecting to MongoDB...
        ✓ Connected successfully

Step 2: Skipping clear (use --clear to reset)

Step 3: Generating data for 7 days...
        [1/3] cow1...~7000 docs
        [2/3] cow2...~7200 docs
        [3/3] cow3...~6800 docs

Step 4: Verifying insertion...
        ✓ 21000 total documents in collection

======================================================================
BACKFILL SUMMARY
======================================================================

Total documents: 21000

cow1:
  Documents: 7000
  First reading: 2025-10-27 01:30:00+0000
  Last reading: 2025-11-02 23:45:00+0000

cow2:
  Documents: 7200
  First reading: 2025-10-27 00:15:00+0000
  Last reading: 2025-11-02 23:50:00+0000

cow3:
  Documents: 6800
  First reading: 2025-10-27 02:00:00+0000
  Last reading: 2025-11-02 23:30:00+0000

Overall time range: 2025-10-27 00:15:00+0000 to 2025-11-02 23:50:00+0000

✓ Backfill complete!
```

## Data Format

Each document inserted has this structure:

```json
{
  "ts": ISODate("2025-11-02T15:30:45.000Z"),  // Server timestamp (UTC)
  "uuid": "cow1",                              // Cow identifier
  "weight": 5.42,                              // Remaining feed (kg)
  "temp": 27.83                                // Ambient temperature (°C)
}
```

## Configuration

Uses `.env` variables:

- `MONGO_URI` – MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB` – Database name (default: `capstone_d06`)
- `MONGO_COLL` – Collection name (default: `readings`)
- `TZ_OFFSET_MIN` – Timezone offset in minutes (default: `420` = UTC+7)
- `MORNING_SEC` – Morning feeding time in seconds (default: `28800` = 08:00)
- `AFTERNOON_SEC` – Afternoon feeding time in seconds (default: `50400` = 14:00)
- `MIN_FEED_KG` – Min feed per pulse (default: `5`)
- `MAX_FEED_KG` – Max feed per pulse (default: `7`)
- `RFID_MIN_SEC` – Min RFID session duration (default: `300` = 5 min)
- `RFID_MAX_SEC` – Max RFID session duration (default: `600` = 10 min)
- `CONSUMPTION_MAX_KG_PER_HR` – Max eating rate (default: `2`)

## Behavior

### Per Day

1. **08:00 WIB**: Hopper receives 5–7 kg feed
2. **±10 min jitter**: RFID session starts (random within ±10 min window)
3. **5–10 min session**: Cow eats at 0–2 kg/hr rate, sampled every 1 second
4. **14:00 WIB**: Repeat for afternoon pulse

### Data Generation

- **Time range**: N days backwards from now (UTC)
- **Sampling**: 1-second intervals during RFID sessions only
- **Volume per cow per day**: ~600–1200 documents (2 sessions × 5–10 min × 60 sec/min)
- **Insertion**: Direct to MongoDB, no MQTT

## Verify Data

```bash
# Count documents per cow
mongosh "mongodb://localhost:27017/capstone_d06" --eval \
  'db.readings.aggregate([{$group:{_id:"$uuid",count:{$sum:1}}}])'

# Get latest readings
mongosh "mongodb://localhost:27017/capstone_d06" --eval \
  'db.readings.find().sort({ts:-1}).limit(10).forEach(d=>printjson(d))'

# Time range
mongosh "mongodb://localhost:27017/capstone_d06" --eval \
  'var first=db.readings.find().sort({ts:1}).limit(1).next(); var last=db.readings.find().sort({ts:-1}).limit(1).next(); print("Range: "+first.ts+" to "+last.ts)'
```

## Performance Notes

- **7 days × 3 cows**: ~21,000 documents (~20–30 seconds insertion)
- **14 days × 3 cows**: ~42,000 documents (~40–60 seconds)
- **30 days × 3 cows**: ~90,000 documents (~120–180 seconds)

All timestamps are **UTC** (converted to WIB for simulation logic only).
