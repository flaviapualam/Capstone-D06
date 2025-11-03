# Data Insertion: Terminal vs Persistent Storage

## Short Answer

**NO** - Stopping the terminal does **NOT** delete the data already inserted into MongoDB.

---

## How It Works

### Data Flow
```
feeder-sim.py (Terminal Process)
    ↓ publishes to MQTT
test.mosquitto.org (Cloud Broker)
    ↓ message retained on broker
ingestor.py (Terminal Process)
    ↓ receives message
MongoDB (Persistent Database)
    ↓ STORES DATA PERMANENTLY
```

### Key Points

1. **MongoDB is Persistent** ✅
   - Once data is inserted into MongoDB, it stays there
   - Even if terminal closes, database keeps the data
   - Data survives computer restarts

2. **Backfill Data is Already In MongoDB** ✅
   - Your 19,721 documents are already stored permanently
   - They won't disappear when you close terminal
   - You can query them anytime

3. **Live Insertion (feeder-sim + ingestor) Depends on Terminal** ⚠️
   - If you run `feeder-sim.py` and `ingestor.py` in terminal and then close it:
     - Both processes stop
     - New data won't be published/inserted
     - But existing data remains in MongoDB

---

## Scenarios

### Scenario 1: Backfill Data (Your Current Data)
```
python3 backfill_realistic.py --days 2

↓ (inserts 19,721 documents to MongoDB)

Close terminal

↓ (terminal stops, but...)

mongosh mongodb://localhost:27017/capstone_d06
db.readings.countDocuments({})  
# Result: 19,721 ✓ DATA STILL THERE!
```

### Scenario 2: Live Insertion (MQTT + Ingestor)
```
Terminal 1: python3 ingestor/ingestor.py
Terminal 2: python3 feeder-sim/feeder_sim.py

↓ (data being inserted in real-time)

Close Terminal 1 or 2

↓ (processes stop)

Insertion STOPS, but existing data remains
```

### Scenario 3: Check Data After Terminal Closes
```
# Terminal 1: Run backfill
python3 backfill_realistic.py --days 1

# Close terminal

# Later, open new terminal:
mongosh mongodb://localhost:27017/capstone_d06
db.readings.countDocuments({})
# Still shows the data! ✓
```

---

## MongoDB Data Persistence

Your MongoDB database has **3 levels of permanence**:

| Level | What Happens | Survives |
|-------|-------------|----------|
| Memory | Data loaded in RAM | Terminal closed ❌ |
| Disk | Data written to disk | Computer restart ✅ |
| Replica | Data replicated to backup | Server failure ✅ |

Your data is on **Disk + Replica**, so it's permanent.

---

## Visual Timeline

### Life of Backfill Data
```
Time 0:  Run: python3 backfill_realistic.py
         ↓
Time 5:  19,721 documents inserted to MongoDB disk
         ↓
Time 10: Close terminal (process stops)
         But data remains on disk!
         ↓
Time 100: Open new terminal
          mongosh: Still see 19,721 documents ✓
         ↓
Time 1000: Computer restart
           MongoDB restarts
           Still see 19,721 documents ✓
```

### Life of Live Insertion
```
Time 0:  Start feeder-sim + ingestor in terminal
         ↓
Time 1-5: New data being inserted (MQTT → ingestor → MongoDB)
         ↓
Time 6:  Close terminal (processes stop)
         Previous data: stays in MongoDB ✓
         New data: stops being inserted ✗
         ↓
Time 7:  Open new terminal
         mongosh: See all old data ✓
         But NO NEW data since time 6
```

---

## What Gets Lost When You Close Terminal?

❌ **Gets Lost:**
- Running processes (feeder-sim, ingestor)
- Console output/logs
- Temporary files in RAM

✅ **Does NOT Get Lost:**
- MongoDB data (persisted to disk)
- File system changes
- Git commits

---

## Best Practices

### To Keep Data Insertion Running 24/7

Use one of these methods:

**Option 1: Background Process (Simple)**
```bash
nohup python3 ingestor/ingestor.py > ingestor.log 2>&1 &
nohup python3 feeder-sim/feeder_sim.py > feeder.log 2>&1 &
# Now you can close terminal - processes keep running
```

**Option 2: tmux (Better)**
```bash
tmux new-session -d -s ingestor "python3 ingestor/ingestor.py"
tmux new-session -d -s feeder "python3 feeder-sim/feeder_sim.py"
# Processes keep running, even if you disconnect
# Reconnect later: tmux attach -t ingestor
```

**Option 3: launchd (macOS Native)**
```bash
# Create .plist file to auto-start on boot
```

**Option 4: systemd (Linux)**
```bash
# Create systemd service file
```

---

## Verify Data Persistence

Test this yourself:

```bash
# Step 1: Insert data
python3 backfill_realistic.py --days 1

# Step 2: Check count
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.countDocuments({})"
# See: 19721

# Step 3: Close terminal completely

# Step 4: Open NEW terminal

# Step 5: Check count again
mongosh mongodb://localhost:27017/capstone_d06 --eval "db.readings.countDocuments({})"
# Still see: 19721 ✓ DATA PERSISTED!
```

---

## Summary

| Question | Answer |
|----------|--------|
| Will data disappear if I close terminal? | NO ✓ |
| Is data in MongoDB permanent? | YES ✓ |
| Will live insertion continue after terminal closes? | NO - must restart |
| Can I query data after terminal closes? | YES ✓ |
| Does computer restart affect data? | NO ✓ |

---

## Your Current Situation

Your 19,721 documents are **safely stored** in MongoDB on disk:
- ✅ Safe if you close terminal
- ✅ Safe if you restart computer
- ✅ Safe to query anytime
- ✓ Already verified to exist!

You can safely close your terminal. The data is not going anywhere! 🎉
