# Cattle Streaming - Data Ingestion & Backfill

Utilities for ingesting cattle sensor data via MQTT and backfilling MongoDB with realistic feeding patterns.

## 📁 Structure

```
├── backfill_realistic.py      # Generate realistic cattle feeding data
├── backfill_realistic_v2.py   # Advanced: 3 cows, 7 days, anomalies + ground-truth
├── backfill.py                # Backfill MongoDB with test data
├── ingestor/
│   └── ingestor.py           # MQTT subscriber - live data ingestion
├── feeder-sim/
│   ├── feeder_sim.py         # Simulate feeder device sending MQTT
│   └── cows.json             # Cattle configuration
├── scripts/
│   └── init_timeseries.py    # Initialize MongoDB collections
├── requirements.txt           # Python dependencies
└── .env                       # Configuration (MongoDB, MQTT)
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd cattle-streaming
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure .env

```bash
cp .env.example .env
```

Edit `.env`:
```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=capstone_d06
MONGO_COLL=readings
MQTT_BROKER=test.mosquitto.org
MQTT_PORT=1883
MQTT_TOPIC=cattle/sensor
```

### 3. Initialize MongoDB

```bash
python scripts/init_timeseries.py
```

### 4. Backfill Test Data

**Option A: Advanced Realistic Simulation (Recommended for ML Training)**
```bash
# Default: 7 days from today with anomalies
python backfill_realistic_v2.py

# Custom date range and seed
python backfill_realistic_v2.py --start-date 2025-10-28 --n-days 7 --seed 42

# Dry run (generate but don't write to MongoDB)
python backfill_realistic_v2.py --dry-run

# Full backfill with all options
python backfill_realistic_v2.py \
  --start-date 2025-10-28 \
  --n-days 7 \
  --seed 42 \
  --batch-size 1000 \
  --write-mongo
```

**Option B: Basic Realistic Simulation**
```bash
python backfill_realistic.py

# Or use simple test backfill
python backfill.py
```

### 5. Start Live Ingestion

**Terminal 1 - Feeder Simulator:**
```bash
python feeder-sim/feeder_sim.py
```

**Terminal 2 - Ingestor:**
```bash
python ingestor/ingestor.py
```

## 📊 Data Schema

Sensor readings in MongoDB:
```json
{
  "_id": ObjectId,
  "timestamp": "2025-11-04T10:30:00Z",
  "cow_id": "uuid-string",
  "sensor_id": "uuid-string",
  "eat_duration": 25.5,
  "eat_speed": 2.3,
  "temperature": 38.5,
  "anomaly_score": 0.1,
  "isAnomaly": false
}
```

## 🔧 Key Features

- **Realistic Backfill**: Generates feeding patterns matching real cattle behavior
- **Live MQTT Ingestion**: Subscribe to sensor data from IoT devices
- **MongoDB Time-Series**: Optimized for time-series data queries
- **Configurable Parameters**: Adjust feeding patterns via environment variables

## 📝 Environment Variables

```env
# MongoDB
MONGO_URI              # Connection string
MONGO_DB              # Database name
MONGO_COLL            # Collection name

# MQTT
MQTT_BROKER           # Broker hostname/IP
MQTT_PORT             # Port (default: 1883)
MQTT_TOPIC            # Topic to subscribe/publish

# Feeding Simulation
MORNING_SEC           # Morning feeding time (seconds from midnight)
AFTERNOON_SEC         # Afternoon feeding time
MIN_FEED_KG          # Min feed per meal
MAX_FEED_KG          # Max feed per meal
```

## 🎯 Advanced Simulation: `backfill_realistic_v2.py`

The v2 simulator generates **two MongoDB collections** with realistic cattle feeding data and ground-truth labels for anomaly detection training.

### Collections Generated

#### 1. `sensor_data` - Raw Time-Series Readings

Simulates IoT sensor readings at 5-second intervals:

```json
{
  "_id": ObjectId,
  "timestamp": "2025-10-30T08:12:35Z",
  "uid": "8H13CJ7",
  "weight": 6.34,
  "temp": 30.2,
  "sensor_id": 1
}
```

**Fields:**
- `timestamp`: UTC time of sensor read
- `uid`: Cow RFID UID (or `null` for ghost drops)
- `weight`: Feed container weight in kg
- `temp`: Shelter temperature (°C)
- `sensor_id`: Feeder device identifier

**Characteristics:**
- ~30,000 documents per simulation run
- Exponential decay curves modeling realistic feed consumption
- Gaussian noise (σ = 0.03 kg) for realistic sensor behavior
- Occasional ±0.3 kg spikes (0.5% probability) for sensor validation
- Temperature variations (baseline 28-31°C, heat days 35-36°C)

#### 2. `metadata` - Session Summaries with Ground-Truth

Per-session aggregation with health labels:

```json
{
  "_id": ObjectId,
  "session_id": "2025-10-30_morning_8H13CJ7",
  "uid": "8H13CJ7",
  "sensor_id": 1,
  "date": "2025-10-30",
  "feeding_time": "morning",
  "behavior_label": "normal",
  "feed_consumed_kg": 6.2,
  "duration_min": 62,
  "temp_mean": 29.8,
  "sick_groundtruth": false
}
```

**Fields:**
- `session_id`: Unique session identifier
- `behavior_label`: Feeding behavior type (see below)
- `feed_consumed_kg`: Total feed consumed
- `duration_min`: Session duration in minutes
- `temp_mean`: Average temperature during session
- `sick_groundtruth`: Ground-truth health status

### Simulated Cows & Devices

Three cattle, each mapped to a unique IoT feeder:

| UID       | Sensor ID | Alias  | Details              |
|-----------|-----------|--------|----------------------|
| `8H13CJ7` | 1         | COW_A  | Days 3-5: short_feed |
| `7F41TR2` | 2         | COW_B  | Day 4: no_show       |
| `9K22PQ9` | 3         | COW_C  | Healthy: noise/idle  |

### Behavior Patterns

The simulator injects realistic feeding behaviors with ground-truth labels:

| Behavior          | Description                              | Pattern                | Sick? | Label |
|-------------------|------------------------------------------|------------------------|-------|-------|
| **normal**        | Typical meal, complete consumption       | 5.5-7 kg, 50-70 min   | ✗     | `false` |
| **short_feed**    | Stops early, signs of weakness/sickness  | 1-2 kg, 10-20 min     | ✓     | `true` |
| **no_show**       | Cow skips feeding entirely                | 0 kg, 0 min           | ✓     | `true` |
| **idle_near_feeder** | RFID active, minimal consumption       | 0.1-0.3 kg, 30-60 min | ✗     | `false` |
| **ghost_drop**    | Weight drops w/o RFID (scale drift)      | 2-4 kg, 20-40 min     | ✗     | `false` |
| **sensor_noise**  | Erratic readings, normal consumption     | 3-5 kg, 30-50 min     | ✗     | `false` |
| **overeat**       | Excessive consumption (dominance/calib)  | 8-10 kg, 60-80 min    | ✗     | `false` |

### Mathematical Model

Load cell weight curve simulation:

$$\text{weight}(t) = W_0 - C \cdot \left(\frac{t}{T}\right)^\alpha + \mathcal{N}(0, \sigma)$$

Where:
- $W_0$: Initial weight (6.5-7.5 kg)
- $C$: Total consumption (behavior-specific)
- $T$: Session duration
- $\alpha$: Shape parameter (0.9-1.2, random per session)
- $\mathcal{N}(0, \sigma)$: Gaussian noise ($\sigma = 0.03$ kg)

Occasional spikes: $\pm 0.3$ kg with probability 0.005

### Ground-Truth Health Schedule

**Day-by-day injected behaviors** (7-day simulation):

```
Days 1-2:    All cows normal
Day 3:       COW_A: short_feed (sick=true)
Day 4:       COW_A: short_feed (sick=true)
             COW_B: no_show (sick=true)
Day 5:       COW_A: short_feed (sick=true)
Days 6-7:    All cows normal
```

COW_C alternates between `idle_near_feeder` and `sensor_noise` throughout (healthy).

### CLI Arguments

```bash
python backfill_realistic_v2.py [OPTIONS]
```

| Argument        | Type    | Default                | Description |
|-----------------|---------|------------------------|-------------|
| `--start-date`  | str     | 7 days ago             | Start date (YYYY-MM-DD) |
| `--n-days`      | int     | 7                      | Days to simulate |
| `--seed`        | int     | random                 | Random seed (reproducibility) |
| `--batch-size`  | int     | 1000                   | MongoDB insert batch size |
| `--write-mongo` | flag    | True                   | Write to MongoDB |
| `--dry-run`     | flag    | False                  | Generate without writing |

### Example Runs

**1. Default: 7 days from a week ago**
```bash
python backfill_realistic_v2.py
```
Output: ~30,000 sensor readings + 42 session summaries

**2. Reproducible run with fixed seed**
```bash
python backfill_realistic_v2.py --seed 42
```
Same data every time (good for testing, demos)

**3. Custom date range**
```bash
python backfill_realistic_v2.py --start-date 2025-10-20 --n-days 14
```
14 days from Oct 20 → 84 sessions

**4. Dry run (no MongoDB write)**
```bash
python backfill_realistic_v2.py --dry-run --seed 123
```
Preview data without database overhead

**5. High performance (larger batches)**
```bash
python backfill_realistic_v2.py --batch-size 5000 --write-mongo
```
Faster inserts for large datasets

### Output Summary

After running, you'll see:

```
==============================================================================
REALISTIC CATTLE FEEDING DATA SIMULATION — 3 COWS / 7 DAYS
==============================================================================

📋 CONFIGURATION:
   Start Date: 2025-10-28 (UTC)
   Days: 7
   Seed: 42
   MongoDB: mongodb://localhost:27017 / capstone_d06
   Write: Yes

🐄 COWS:
   COW_A (8H13CJ7) - Sensor 1
   COW_B (7F41TR2) - Sensor 2
   COW_C (9K22PQ9) - Sensor 3

📅 SCHEDULE:
   Morning: 08:00 (±2 min)
   Afternoon: 14:00 (±2 min)
   Normal duration: 50-70 min
   Feed per meal: 6.5-7.5 kg

⚠️  GROUND-TRUTH HEALTH SCHEDULE:
   COW_A (8H13CJ7): short_feed on days 3-5 (sick)
   COW_B (7F41TR2): no_show on day 4 (sick)
   COW_C (9K22PQ9): idle_near_feeder/sensor_noise (healthy)

✅ VERIFICATION:
   sensor_data collection: 30124 documents
   metadata collection: 42 documents

   Per-cow breakdown:
      COW_A: 10042 sensor docs, 14 sessions
      COW_B: 10041 sensor docs, 14 sessions
      COW_C: 10041 sensor docs, 14 sessions

   Behavior distribution:
      ghost_drop: 6 sessions
      idle_near_feeder: 7 sessions
      no_show: 1 session
      normal: 21 sessions
      sensor_noise: 7 sessions

   Health stats:
      Sick sessions: 8
      Healthy sessions: 34

✓ SIMULATION COMPLETE
```

### Use Cases

1. **Isolation Forest Training**
   - Use `metadata.sick_groundtruth` as training labels
   - Features: feed_consumed_kg, duration_min, temp_mean
   - Anomalies: short_feed, no_show

2. **Real-Time Monitoring**
   - Load `sensor_data` for live dashboard
   - Stream detection on behavior patterns

3. **Model Validation**
   - Split by date (e.g., days 1-5 train, days 6-7 test)
   - Verify anomaly detection accuracy

4. **Dashboard Visualization**
   - Time-series weight curves per session
   - Temperature overlays
   - Behavior classification

## 🐛 Troubleshooting



### MongoDB Connection Error
```bash
# Check MongoDB is running
mongosh --eval "db.runCommand({ ping: 1 })"

# Start MongoDB
brew services start mongodb-community
```

### MQTT Connection Error
```bash
# Test MQTT broker connectivity
mosquitto_sub -h test.mosquitto.org -t "test"
```

## 📚 Related Documentation

- Backend: See `backend-fastapi-2/` for API endpoints
- Frontend: See `frontend/` for monitoring dashboard
