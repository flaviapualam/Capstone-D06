# services/crud_device.py
import asyncpg
from typing import List, Tuple

async def upsert_device_status(db: asyncpg.Connection, device_data_batch: List[Tuple]):
    query = """
    INSERT INTO device (device_id, status, last_ip, last_seen)
    VALUES ($1, 'ONLINE', $2, $3)
    ON CONFLICT (device_id) DO UPDATE 
    SET 
        status = 'ONLINE',
        last_ip = $2,
        last_seen = $3;
    """
    try:
        await db.executemany(query, device_data_batch)
        print(f"(DEVICE MONITOR) Updated status for {len(device_data_batch)} devices.")
    except Exception as e:
        print(f"Error during device UPSERT: {e}")