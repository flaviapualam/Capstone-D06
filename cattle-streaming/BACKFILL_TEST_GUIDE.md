# How to Test & Compare Backfill Data in MongoDB

Karena terminal agak bermasalah, berikut adalah panduan lengkap untuk test backfill data secara manual.

## Quick Test (Manual)

### Step 1: Open MongoDB Shell
```bash
mongosh "mongodb://localhost:27017"
```

### Step 2: Clear Database (Optional)
```javascript
use capstone_d06
db.readings.deleteMany({})
print("Database cleared")
```

### Step 3: Run Current Backfill (3 hari)
Di terminal baru:
```bash
cd cattle-streaming
python3 backfill.py --days 3 --clear
```

### Step 4: Check Data in MongoDB
```javascript
// Jumlah total
db.readings.countDocuments({})

// Per cow
db.readings.countDocuments({uuid: "cow1"})
db.readings.countDocuments({uuid: "cow2"})
db.readings.countDocuments({uuid: "cow3"})

// Lihat sample
db.readings.findOne({uuid: "cow1"}, {sort: {ts: 1}})
db.readings.findOne({uuid: "cow1"}, {sort: {ts: -1}})

// Stats weight
db.readings.aggregate([
  {$match: {uuid: "cow1"}},
  {$group: {_id: null, min: {$min: "$weight"}, max: {$max: "$weight"}, avg: {$avg: "$weight"}}}
])
```

### Step 5: Clear & Run Realistic
```javascript
db.readings.deleteMany({})
```

Di terminal:
```bash
python3 backfill_realistic.py --days 3 --clear
```

### Step 6: Compare Numbers
```javascript
// Sama seperti step 4
db.readings.countDocuments({})
```

---

## Expected Results

### Current Mode (backfill.py) - 3 hari × 3 sapi

```
Total documents: ~18,000-21,000
  cow1: ~6,000-7,000
  cow2: ~6,000-7,000
  cow3: ~6,000-7,000

Per day per cow: ~600-700 docs

Weight pattern:
  Min: 0.00 kg (habis)
  Max: 7.00 kg (penuh)
  Avg: ~2-3 kg (kebanyakan sisa)
  
Interpretasi: Banyak session pendek, pakan jarang habis
```

### Realistic Mode (backfill_realistic.py) - 3 hari × 3 sapi

```
Total documents: ~3,600-4,800
  cow1: ~1,200-1,600
  cow2: ~1,200-1,600
  cow3: ~1,200-1,600

Per day per cow: ~400-500 docs

Weight pattern:
  Min: 0.00 kg (habis)
  Max: 12.00 kg (penuh)
  Avg: ~6 kg (tengah-tengah)
  
Interpretasi: Sedikit session panjang, pakan habis per meal
```

---

## Key Differences

| Metrik | Current | Realistic |
|--------|---------|-----------|
| **Total docs (3 hari)** | ~20,000 | ~4,000 |
| **Docs per day** | ~2,200 | ~440 |
| **Ratio** | 5x MORE | baseline |
| **Max weight** | 7 kg | 12 kg |
| **Min weight** | 0 kg | 0 kg |
| **Avg weight** | 2-3 kg | 5-6 kg |
| **% habis** | Jarang (session pendek) | Selalu (session panjang) |

---

## Detailed MongoDB Queries

### 1. Count Documents
```javascript
db.readings.countDocuments({})
db.readings.countDocuments({uuid: "cow1"})
```

### 2. Time Range per Cow
```javascript
db.readings.aggregate([
  {$group: {
    _id: "$uuid",
    first: {$min: "$ts"},
    last: {$max: "$ts"},
    count: {$sum: 1}
  }}
])
```

### 3. Weight Statistics
```javascript
db.readings.aggregate([
  {$group: {
    _id: "$uuid",
    min_weight: {$min: "$weight"},
    max_weight: {$max: "$weight"},
    avg_weight: {$avg: "$weight"},
    total_docs: {$sum: 1}
  }},
  {$sort: {_id: 1}}
])
```

### 4. Session Duration Analysis
```javascript
// Lihat berapa lama setiap feeding session
// Query: Cari "jumps" dalam weight (naik = new feed)
db.readings.find({uuid: "cow1"}, {ts: 1, weight: 1, _id: 0}).limit(100)
```

### 5. Sample Recent Data
```javascript
db.readings.find({uuid: "cow1"})
  .sort({ts: -1})
  .limit(10)
  .pretty()
```

### 6. Compare Meals
```javascript
// Morning meal (08:00)
db.readings.find({
  uuid: "cow1",
  ts: {$gte: new Date("2025-11-03T08:00:00Z"), $lt: new Date("2025-11-03T10:00:00Z")}
}).count()

// Afternoon meal (14:00)
db.readings.find({
  uuid: "cow1",
  ts: {$gte: new Date("2025-11-03T14:00:00Z"), $lt: new Date("2025-11-03T16:00:00Z")}
}).count()
```

---

## Python Script to Compare

Jika ingin run via Python:

```python
from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017')
coll = client['capstone_d06']['readings']

# Count
total = coll.count_documents({})
print(f"Total: {total}")

# Per cow
for cow in ["cow1", "cow2", "cow3"]:
    count = coll.count_documents({"uuid": cow})
    print(f"{cow}: {count}")

# Stats
stats = list(coll.aggregate([
    {$group: {
        _id: "$uuid",
        docs: {$sum: 1},
        min_w: {$min: "$weight"},
        max_w: {$max: "$weight"},
        avg_w: {$avg: "$weight"}
    }}
]))[0]

print(f"\n{stats}")
```

---

## Files untuk Test

- `backfill.py` - Run current mode: `python3 backfill.py --days 3`
- `backfill_realistic.py` - Run realistic mode: `python3 backfill_realistic.py --days 3`
- `inline_backfill_test.py` - Automated test: `python3 inline_backfill_test.py`
- `compare_backfill.py` - Compare mode: `python3 compare_backfill.py`
- `run_backfill.py` - Simple runner: `python3 run_backfill.py current` atau `python3 run_backfill.py realistic`

---

## Troubleshooting

### MongoDB tidak connect
```bash
# Check if MongoDB running
ps aux | grep mongod

# Start MongoDB
brew services start mongodb-community
# or
mongod --config /usr/local/etc/mongod.conf
```

### Terminal stuck
Coba terminal baru atau:
```bash
# Restart shell
exec bash

# Or use screen
screen -S backfill
python3 backfill.py --days 3
# Ctrl+A then D to detach
```

### Script hang
Gunakan timeout:
```bash
timeout 120 python3 backfill.py --days 3
```

---

## Expected Output (Current Mode)

```
======================================================================
Cattle Streaming Backfill Agent
======================================================================

Configuration:
  MongoDB URI: mongodb://localhost:27017
  Database: capstone_d06, Collection: readings
  Days to backfill: 3
  Cows: cow1, cow2, cow3
  Feeding times (WIB): 08:00, 14:00
  RFID window: 300-600 seconds
  Consumption: 0-2 kg/hr

Step 1: Connecting to MongoDB...
        ✓ Connected successfully

Step 2: Skipping clear (use --clear to reset)

Step 3: Generating data for 3 days...
        [1/3] cow1...~6500 docs
        [2/3] cow2...~7100 docs
        [3/3] cow3...~6800 docs

Step 4: Verifying insertion...
        ✓ 20400 total documents in collection

======================================================================
BACKFILL SUMMARY
======================================================================

Total documents: 20400

cow1:
  Documents: 6500
  First reading: 2025-11-00 09:30:12+0000
  Last reading: 2025-11-03 23:45:50+0000

cow2:
  Documents: 7100
  First reading: 2025-11-00 08:15:42+0000
  Last reading: 2025-11-03 23:52:30+0000

cow3:
  Documents: 6800
  First reading: 2025-11-00 09:45:22+0000
  Last reading: 2025-11-03 23:40:15+0000

Overall time range: 2025-11-00 08:15:42+0000 to 2025-11-03 23:52:30+0000

✓ Backfill complete!
```

---

Sekarang, apa yang ingin kamu lihat lebih detail dari data yang sudah di-insert? 🎯
