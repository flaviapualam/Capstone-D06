#!/usr/bin/env python3
"""
===============================================================================
🐄 CATTLE FEEDING DATA SIMULATOR — BACKFILL (1 MONTH) MODE
===============================================================================

Generate realistic historical sensor data for 3 cattle feeder devices over 
a full 30-day period and insert it directly into TimescaleDB table `output_sensor`.

Author: Capstone D06 Team
Date: 2025-11-13
===============================================================================
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import random
import psycopg2
from psycopg2.extras import execute_batch
import numpy as np
from dataclasses import dataclass
import logging


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

DEVICE_IDS = ["1", "2", "3"]
RFID_MAPPING = {
    "1": "8H13CJ7",  # Will be sick on days 10-12
    "2": "7F41TR2",  # Will be sick (no-show) on day 20
    "3": "9K22PQ9",  # Healthy throughout
}

SHARED_IP = "192.168.1.100"
FEEDING_TIMES = ["08:00", "14:00"]  # Daily feeding schedule
SAMPLING_RATE_SECONDS = 1

# Feeding behavior parameters
NORMAL_FEEDING_DURATION_MIN = 60  # minutes
FEEDING_DURATION_JITTER_MIN = 10
FEEDING_START_JITTER_MIN = 2
BUFFER_TIME_SECONDS = 60  # 1 minute at start/end with no weight change

# Load cell parameters
INITIAL_WEIGHT_MIN = 6.5  # kg
INITIAL_WEIGHT_MAX = 7.5
CONSUMPTION_RATE_MIN = 0.002  # kg/s
CONSUMPTION_RATE_MAX = 0.0025
WEIGHT_NOISE_STD = 0.005
SPIKE_PROBABILITY = 0.005
SPIKE_MAGNITUDE = 0.3

# Temperature parameters
TEMP_MIN = 28.0  # °C
TEMP_MAX = 31.0
TEMP_DRIFT_RATE = 0.02  # °C/min
TEMP_UPDATE_INTERVAL = 60  # seconds

# Anomaly parameters (ground truth)
SICK_COW_1_DAYS = (10, 12)  # Days 10-12 inclusive
SICK_COW_2_DAY = 20  # Day 20 no-show
SHORT_FEEDING_DURATION_MIN = 20  # Sick cow feeds for only ~20 min


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SensorReading:
    """Single sensor reading from a feeder device"""
    timestamp: datetime
    device_id: str
    rfid_id: Optional[str]
    weight: float
    temperature_c: float
    ip: str


@dataclass
class FeedingSession:
    """A single feeding session for one device"""
    device_id: str
    start_time: datetime
    duration_min: float
    is_anomaly: bool
    anomaly_type: Optional[str]  # 'short_feeding', 'no_show', None


# ============================================================================
# SIMULATION LOGIC
# ============================================================================

class CattleDataSimulator:
    """Generate realistic cattle feeding sensor data"""
    
    def __init__(self, start_date: datetime, n_days: int, seed: int = 42):
        self.start_date = start_date
        self.n_days = n_days
        self.end_date = start_date + timedelta(days=n_days)
        
        random.seed(seed)
        np.random.seed(seed)
        
        self.logger = logging.getLogger(__name__)
    
    def generate_feeding_schedule(self) -> Dict[str, List[FeedingSession]]:
        """
        Generate feeding schedule for all devices over the simulation period.
        Includes ground truth anomalies.
        """
        schedule = {device_id: [] for device_id in DEVICE_IDS}
        
        for day in range(self.n_days):
            current_date = self.start_date + timedelta(days=day)
            day_number = day + 1  # 1-indexed for clarity
            
            for device_id in DEVICE_IDS:
                for feeding_time_str in FEEDING_TIMES:
                    session = self._create_feeding_session(
                        device_id, current_date, feeding_time_str, day_number
                    )
                    if session:  # May be None for no-show anomalies
                        schedule[device_id].append(session)
        
        return schedule
    
    def _create_feeding_session(
        self, 
        device_id: str, 
        date: datetime, 
        time_str: str,
        day_number: int
    ) -> Optional[FeedingSession]:
        """Create a single feeding session with potential anomalies"""
        
        # Parse base time
        hour, minute = map(int, time_str.split(":"))
        base_time = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Add random jitter
        jitter_seconds = random.randint(
            -FEEDING_START_JITTER_MIN * 60,
            FEEDING_START_JITTER_MIN * 60
        )
        start_time = base_time + timedelta(seconds=jitter_seconds)
        
        # Check for anomalies
        is_anomaly = False
        anomaly_type = None
        duration_min = NORMAL_FEEDING_DURATION_MIN + random.uniform(
            -FEEDING_DURATION_JITTER_MIN, FEEDING_DURATION_JITTER_MIN
        )
        
        # Device 1: Short feeding on days 10-12
        if device_id == "1" and SICK_COW_1_DAYS[0] <= day_number <= SICK_COW_1_DAYS[1]:
            is_anomaly = True
            anomaly_type = "short_feeding"
            duration_min = SHORT_FEEDING_DURATION_MIN + random.uniform(-5, 5)
            self.logger.info(
                f"Anomaly: Device {device_id} day {day_number} - Short feeding ({duration_min:.1f} min)"
            )
        
        # Device 2: No-show on day 20
        if device_id == "2" and day_number == SICK_COW_2_DAY:
            is_anomaly = True
            anomaly_type = "no_show"
            self.logger.info(f"Anomaly: Device {device_id} day {day_number} - No show")
            return None  # No session created
        
        return FeedingSession(
            device_id=device_id,
            start_time=start_time,
            duration_min=duration_min,
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type
        )
    
    def generate_session_data(self, session: FeedingSession) -> List[SensorReading]:
        """Generate sensor readings for a single feeding session"""
        
        readings = []
        device_id = session.device_id
        rfid_id = RFID_MAPPING[device_id]
        
        # Session parameters
        start_time = session.start_time
        duration_seconds = int(session.duration_min * 60)
        
        # Weight parameters
        initial_weight = random.uniform(INITIAL_WEIGHT_MIN, INITIAL_WEIGHT_MAX)
        consumption_rate = random.uniform(CONSUMPTION_RATE_MIN, CONSUMPTION_RATE_MAX)
        
        # Temperature parameters
        current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
        temp_drift = random.uniform(-TEMP_DRIFT_RATE, TEMP_DRIFT_RATE)
        
        current_weight = initial_weight
        
        # Buffer phase (start): Cow approaches, no eating yet
        for i in range(BUFFER_TIME_SECONDS):
            timestamp = start_time + timedelta(seconds=i)
            
            # Update temperature every 60s
            if i % TEMP_UPDATE_INTERVAL == 0:
                current_temp += temp_drift * (TEMP_UPDATE_INTERVAL / 60)
                current_temp = np.clip(current_temp, TEMP_MIN, TEMP_MAX)
            
            # Weight stays constant with small noise
            weight = current_weight + np.random.normal(0, WEIGHT_NOISE_STD * 0.5)
            
            readings.append(SensorReading(
                timestamp=timestamp,
                device_id=device_id,
                rfid_id=rfid_id,
                weight=max(0, weight),
                temperature_c=round(current_temp, 2),
                ip=SHARED_IP
            ))
        
        # Active feeding phase
        feeding_seconds = duration_seconds - 2 * BUFFER_TIME_SECONDS
        for i in range(feeding_seconds):
            timestamp = start_time + timedelta(seconds=BUFFER_TIME_SECONDS + i)
            
            # Update temperature
            if (BUFFER_TIME_SECONDS + i) % TEMP_UPDATE_INTERVAL == 0:
                current_temp += temp_drift * (TEMP_UPDATE_INTERVAL / 60)
                current_temp = np.clip(current_temp, TEMP_MIN, TEMP_MAX)
            
            # Decrease weight (consumption)
            current_weight -= consumption_rate
            
            # Add noise
            noise = np.random.normal(0, WEIGHT_NOISE_STD)
            
            # Random spike
            if random.random() < SPIKE_PROBABILITY:
                noise += random.choice([-1, 1]) * SPIKE_MAGNITUDE
            
            weight = current_weight + noise
            
            readings.append(SensorReading(
                timestamp=timestamp,
                device_id=device_id,
                rfid_id=rfid_id,
                weight=max(0, weight),
                temperature_c=round(current_temp, 2),
                ip=SHARED_IP
            ))
        
        # Buffer phase (end): Cow leaves
        for i in range(BUFFER_TIME_SECONDS):
            timestamp = start_time + timedelta(
                seconds=BUFFER_TIME_SECONDS + feeding_seconds + i
            )
            
            if (BUFFER_TIME_SECONDS + feeding_seconds + i) % TEMP_UPDATE_INTERVAL == 0:
                current_temp += temp_drift * (TEMP_UPDATE_INTERVAL / 60)
                current_temp = np.clip(current_temp, TEMP_MIN, TEMP_MAX)
            
            # Weight stays constant
            weight = current_weight + np.random.normal(0, WEIGHT_NOISE_STD * 0.5)
            
            readings.append(SensorReading(
                timestamp=timestamp,
                device_id=device_id,
                rfid_id=rfid_id,
                weight=max(0, weight),
                temperature_c=round(current_temp, 2),
                ip=SHARED_IP
            ))
        
        return readings
    
    def generate_idle_data(
        self, 
        device_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[SensorReading]:
        """
        Generate idle sensor readings (no cow present) between feeding sessions.
        Sample at lower rate (every 60s) to reduce data volume.
        """
        readings = []
        
        current_time = start_time
        current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
        temp_drift = random.uniform(-TEMP_DRIFT_RATE / 2, TEMP_DRIFT_RATE / 2)
        
        while current_time < end_time:
            # Update temperature
            current_temp += temp_drift
            current_temp = np.clip(current_temp, TEMP_MIN, TEMP_MAX)
            
            readings.append(SensorReading(
                timestamp=current_time,
                device_id=device_id,
                rfid_id=None,  # No cow present
                weight=0.0,  # No food loaded
                temperature_c=round(current_temp, 2),
                ip=SHARED_IP
            ))
            
            current_time += timedelta(seconds=60)  # Sample every minute
        
        return readings
    
    def generate_all_data(self) -> List[SensorReading]:
        """Generate complete dataset for all devices"""
        
        self.logger.info(f"Generating feeding schedule for {self.n_days} days...")
        schedule = self.generate_feeding_schedule()
        
        all_readings = []
        
        for device_id in DEVICE_IDS:
            self.logger.info(f"Generating data for device {device_id}...")
            
            sessions = sorted(schedule[device_id], key=lambda s: s.start_time)
            device_start = self.start_date
            
            for session in sessions:
                # Generate idle data before session
                if device_start < session.start_time:
                    idle_readings = self.generate_idle_data(
                        device_id, device_start, session.start_time
                    )
                    all_readings.extend(idle_readings)
                
                # Generate session data
                session_readings = self.generate_session_data(session)
                all_readings.extend(session_readings)
                
                # Update next start time
                session_end = session.start_time + timedelta(minutes=session.duration_min)
                device_start = session_end
            
            # Generate idle data after last session until end date
            if device_start < self.end_date:
                idle_readings = self.generate_idle_data(
                    device_id, device_start, self.end_date
                )
                all_readings.extend(idle_readings)
        
        # Sort all readings by timestamp
        all_readings.sort(key=lambda r: (r.timestamp, r.device_id))
        
        self.logger.info(f"Generated {len(all_readings):,} total readings")
        return all_readings


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

class TimescaleDBWriter:
    """Handle TimescaleDB connections and batch inserts"""
    
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self.logger = logging.getLogger(__name__)
    
    def insert_readings(self, readings: List[SensorReading], batch_size: int = 5000):
        """Insert sensor readings into output_sensor table"""
        
        self.logger.info(f"Connecting to TimescaleDB...")
        conn = psycopg2.connect(self.conn_string)
        
        try:
            cursor = conn.cursor()
            
            # Prepare data for batch insert
            insert_query = """
                INSERT INTO output_sensor 
                (timestamp, device_id, rfid_id, weight, temperature_c, ip)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            total_batches = (len(readings) + batch_size - 1) // batch_size
            
            for batch_idx in range(0, len(readings), batch_size):
                batch = readings[batch_idx:batch_idx + batch_size]
                
                batch_data = [
                    (
                        r.timestamp,
                        r.device_id,
                        r.rfid_id,
                        r.weight,
                        r.temperature_c,
                        r.ip
                    )
                    for r in batch
                ]
                
                execute_batch(cursor, insert_query, batch_data, page_size=batch_size)
                conn.commit()
                
                current_batch = batch_idx // batch_size + 1
                self.logger.info(
                    f"Inserted batch {current_batch}/{total_batches} "
                    f"({len(batch):,} rows)"
                )
            
            self.logger.info(f"✓ Successfully inserted {len(readings):,} readings")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error inserting data: {e}")
            raise
        
        finally:
            cursor.close()
            conn.close()
    
    def verify_data(self, start_date: datetime, n_days: int):
        """Verify inserted data by running some basic queries"""
        
        conn = psycopg2.connect(self.conn_string)
        
        try:
            cursor = conn.cursor()
            
            # Count total rows
            cursor.execute("""
                SELECT COUNT(*) FROM output_sensor
                WHERE timestamp >= %s AND timestamp < %s
            """, (start_date, start_date + timedelta(days=n_days)))
            
            total_rows = cursor.fetchone()[0]
            self.logger.info(f"Total rows in range: {total_rows:,}")
            
            # Count by device
            cursor.execute("""
                SELECT device_id, COUNT(*) 
                FROM output_sensor
                WHERE timestamp >= %s AND timestamp < %s
                GROUP BY device_id
                ORDER BY device_id
            """, (start_date, start_date + timedelta(days=n_days)))
            
            for device_id, count in cursor.fetchall():
                self.logger.info(f"  Device {device_id}: {count:,} rows")
            
            # Sample some feeding sessions (where rfid_id is not null)
            cursor.execute("""
                SELECT device_id, COUNT(*), 
                       MIN(timestamp), MAX(timestamp)
                FROM output_sensor
                WHERE timestamp >= %s AND timestamp < %s
                  AND rfid_id IS NOT NULL
                GROUP BY device_id
                ORDER BY device_id
            """, (start_date, start_date + timedelta(days=n_days)))
            
            self.logger.info("\nFeeding session summary (rfid_id present):")
            for device_id, count, min_ts, max_ts in cursor.fetchall():
                self.logger.info(
                    f"  Device {device_id}: {count:,} readings "
                    f"from {min_ts} to {max_ts}"
                )
            
        finally:
            cursor.close()
            conn.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def setup_logging(verbose: bool):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate 30-day cattle feeding data backfill for TimescaleDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python backfill_monthly_timescale.py \\
    --start-date 2025-10-01 \\
    --pg-conn "postgresql://user:pass@localhost:5432/cattle_dss"
        """
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        help="Start date for backfill (YYYY-MM-DD). Default: 30 days ago"
    )
    
    parser.add_argument(
        "--n-days",
        type=int,
        default=30,
        help="Number of days to generate (default: 30)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Batch size for database inserts (default: 5000)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    
    parser.add_argument(
        "--pg-conn",
        type=str,
        required=True,
        help="PostgreSQL/TimescaleDB connection string"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate data but don't insert into database"
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    # Parse start date
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {args.start_date}. Use YYYY-MM-DD")
        sys.exit(1)
    
    logger.info("=" * 80)
    logger.info("🐄 CATTLE FEEDING DATA SIMULATOR — BACKFILL MODE")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"Duration: {args.n_days} days")
    logger.info(f"Devices: {', '.join(DEVICE_IDS)}")
    logger.info(f"Random seed: {args.seed}")
    logger.info(f"Batch size: {args.batch_size:,}")
    logger.info("=" * 80)
    
    # Generate data
    simulator = CattleDataSimulator(start_date, args.n_days, args.seed)
    
    logger.info("\n📊 Generating sensor data...")
    start_time = datetime.now()
    
    readings = simulator.generate_all_data()
    
    generation_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"✓ Data generation completed in {generation_time:.1f}s")
    logger.info(f"✓ Generated {len(readings):,} sensor readings")
    
    # Estimate data size
    estimated_size_mb = len(readings) * 100 / 1024 / 1024  # ~100 bytes per row
    logger.info(f"✓ Estimated data size: ~{estimated_size_mb:.1f} MB")
    
    if args.dry_run:
        logger.info("\n🔍 DRY RUN MODE - No data will be inserted")
        logger.info(f"Sample readings (first 5):")
        for reading in readings[:5]:
            logger.info(f"  {reading}")
        return
    
    # Insert into database
    logger.info(f"\n💾 Inserting data into TimescaleDB...")
    db_writer = TimescaleDBWriter(args.pg_conn)
    
    insert_start = datetime.now()
    db_writer.insert_readings(readings, args.batch_size)
    insert_time = (datetime.now() - insert_start).total_seconds()
    
    logger.info(f"✓ Database insertion completed in {insert_time:.1f}s")
    logger.info(f"✓ Insert rate: {len(readings) / insert_time:.0f} rows/second")
    
    # Verify
    logger.info(f"\n🔍 Verifying inserted data...")
    db_writer.verify_data(start_date, args.n_days)
    
    total_time = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "=" * 80)
    logger.info(f"✓ COMPLETE! Total time: {total_time:.1f}s")
    logger.info("=" * 80)
    logger.info("\n📋 Ground truth anomalies:")
    logger.info(f"  • Device 1 (RFID: {RFID_MAPPING['1']}): Short feeding on days {SICK_COW_1_DAYS[0]}-{SICK_COW_1_DAYS[1]}")
    logger.info(f"  • Device 2 (RFID: {RFID_MAPPING['2']}): No-show on day {SICK_COW_2_DAY}")
    logger.info(f"  • Device 3 (RFID: {RFID_MAPPING['3']}): Normal (healthy)")
    logger.info("\nFor detailed documentation, see groundtruth.md")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
