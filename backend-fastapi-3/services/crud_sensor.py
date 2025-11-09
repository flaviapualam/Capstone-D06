# services/crud_sensor.py
import asyncpg
from typing import List, Tuple

async def batch_insert_sensor_data(db: asyncpg.Connection, data_batch: List[Tuple]):
    query = """
    INSERT INTO output_sensor ("timestamp", device_id, rfid_id, weight, temperature_c, ip)
    VALUES ($1, $2, $3, $4, $5, $6);
    """
    
    try:
        await db.executemany(query, data_batch)
        print(f"(BATCH INSERT) Successfully inserted {len(data_batch)} records.")
    except Exception as e:
        print(f"Error during batch insert: {e}")