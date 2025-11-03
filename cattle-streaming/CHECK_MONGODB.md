# How to Check Data in MongoDB

## Quick Start: 3 Ways to Check

### Option 1: Using `mongosh` (Interactive Shell) ⭐ EASIEST

```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017/capstone_d06

# Then run these commands:

# 1. Count total documents
db.readings.countDocuments({})

# 2. Count per cow
db.readings.countDocuments({uuid: "cow1"})
db.readings.countDocuments({uuid: "cow2"})
db.readings.countDocuments({uuid: "cow3"})

# 3. See first 5 documents
db.readings.find().limit(5)

# 4. See latest 5 documents
db.readings.find().sort({ts: -1}).limit(5)

# 5. Get statistics per cow
db.readings.aggregate([
  {$group: {
    _id: "$uuid",
    count: {$sum: 1},
    min_weight: {$min: "$weight"},
    max_weight: {$max: "$weight"},
    avg_weight: {$avg: "$weight"}
  }},
  {$sort: {_id: 1}}
])

# 6. Exit
exit
```

---

### Option 2: One-Line Commands (No Interactive Shell)

```bash
# Total count
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.countDocuments({})"

# Per cow
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.countDocuments({uuid: 'cow1'})"

# First 5 documents
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.find().limit(5).toArray()"

# Latest 5 documents
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.find().sort({ts: -1}).limit(5).toArray()"

# Statistics
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.aggregate([{\\$group: {_id: '\\$uuid', count: {\\$sum: 1}, min: {\\$min: '\\$weight'}, max: {\\$max: '\\$weight'}, avg: {\\$avg: '\\$weight'}}}]).toArray()"
```

---

### Option 3: Using Python Script

Create a file `check_mongodb.py`:

```python
#!/usr/bin/env python3
from pymongo import MongoClient

# Connect
client = MongoClient('mongodb://localhost:27017')
db = client['capstone_d06']
coll = db['readings']

# Total count
total = coll.count_documents({})
print(f"Total documents: {total}\n")

# Per cow
print("Documents per cow:")
for cow in ['cow1', 'cow2', 'cow3']:
    count = coll.count_documents({'uuid': cow})
    print(f"  {cow}: {count}")

# Statistics
print("\nWeight statistics per cow:")
stats = coll.aggregate([
    {'$group': {
        '_id': '$uuid',
        'count': {'$sum': 1},
        'min': {'$min': '$weight'},
        'max': {'$max': '$weight'},
        'avg': {'$avg': '$weight'}
    }},
    {'$sort': {'_id': 1}}
])

for doc in stats:
    print(f"\n{doc['_id']}:")
    print(f"  Count: {doc['count']}")
    print(f"  Min: {doc['min']:.2f} kg")
    print(f"  Max: {doc['max']:.2f} kg")
    print(f"  Avg: {doc['avg']:.2f} kg")

# Show recent data
print("\nLatest 3 documents:")
for doc in coll.find().sort('ts', -1).limit(3):
    print(f"  {doc['uuid']}: {doc['ts']} - {doc['weight']}kg @ {doc['temp']}°C")

client.close()
```

Run it:
```bash
python3 check_mongodb.py
```

---

## Common Queries

### 1. Check if database exists
```bash
mongosh mongodb://localhost:27017 --eval "db.adminCommand('listDatabases')"
```

### 2. Check if collection exists
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.getCollectionNames()"
```

### 3. Check collection size
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.stats()"
```

### 4. Find documents where weight = 0 (meal finished)
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.find({weight: 0}).limit(10)"
```

### 5. Find documents for a specific cow
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.find({uuid: 'cow1'}).limit(5)"
```

### 6. Find documents in a time range
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.find({ts: {\\$gte: new Date('2025-11-03'), \\$lt: new Date('2025-11-04')}}).limit(5)"
```

### 7. Get average weight per cow
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.aggregate([{\\$group: {_id: '\\$uuid', avg_weight: {\\$avg: '\\$weight'}}}])"
```

---

## Best Practice Commands

### Quick Health Check (Copy & Paste)
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "
let total = db.readings.countDocuments({});
let cow1 = db.readings.countDocuments({uuid: 'cow1'});
let cow2 = db.readings.countDocuments({uuid: 'cow2'});
let cow3 = db.readings.countDocuments({uuid: 'cow3'});
print('Total: ' + total + ', cow1: ' + cow1 + ', cow2: ' + cow2 + ', cow3: ' + cow3);
"
```

### Compare Current vs Realistic
```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "
db.readings.aggregate([
  {\\$group: {
    _id: '\\$uuid',
    count: {\\$sum: 1},
    min_weight: {\\$min: '\\$weight'},
    max_weight: {\\$max: '\\$weight'},
    avg_weight: {\\$avg: '\\$weight'}
  }},
  {\\$sort: {_id: 1}}
]).forEach(doc => print(JSON.stringify(doc, null, 2)))
"
```

---

## What to Look For

✅ **Good Data (Realistic Mode):**
- Min weight = 0.00 kg (meal fully consumed)
- Max weight = 8-12 kg (realistic meal size)
- Average weight = ~5-6 kg (mid-meal point)

❌ **Bad Data (Current Mode):**
- Min weight = 5-7 kg (never consumed, unrealistic)
- Max weight = 5-7 kg (no variation)
- Average weight = ~6 kg (stuck at same level)

---

## Verify Latest Data

Run this after backfill to see the newest data:

```bash
mongosh mongodb://localhost:27017/capstone_d06 --eval "
db.readings.find()
  .sort({ts: -1})
  .limit(1)
  .forEach(doc => {
    print('Latest document:');
    print('  Cow: ' + doc.uuid);
    print('  Time: ' + doc.ts);
    print('  Weight: ' + doc.weight + ' kg');
    print('  Temp: ' + doc.temp + ' °C');
  })
"
```

---

## Troubleshooting

### MongoDB not running?
```bash
# Check if MongoDB is running
mongosh mongodb://localhost:27017 --eval "db.adminCommand('ping')"

# If error, start MongoDB:
brew services start mongodb-community
# or
mongod
```

### Collection not created?
```bash
# Initialize it
python3 scripts/init_timeseries.py
```

### No data in collection?
```bash
# Run backfill
python3 backfill_realistic.py --days 1 --clear
```

---

## Summary

| Task | Command |
|------|---------|
| Total docs | `mongosh ... --eval "db.readings.countDocuments({})"` |
| Docs per cow | `mongosh ... --eval "db.readings.countDocuments({uuid: 'cow1'})"` |
| See data | `mongosh ... --eval "db.readings.find().limit(5)"` |
| Statistics | `mongosh ... --eval "db.readings.aggregate([...])"` |
| Using Python | `python3 check_mongodb.py` |

**Recommended**: Use **Option 1 (mongosh interactive)** for exploring, **Option 2 (one-liners)** for quick checks, **Option 3 (Python)** for automation.
