# services/crud_device.py
import asyncpg
from typing import List, Tuple

async def upsert_device_status(db: asyncpg.Connection, device_data_batch: List[Tuple]):
    """
    Melakukan 'UPSERT' (Update/Insert) pada tabel 'device'.
    - Jika device_id baru, daftarkan.
    - Jika device_id sudah ada, update status, IP, dan last_seen.
    
    Tuple yang diharapkan: (device_id, last_ip, last_seen)
    """
    # Ini adalah query "UPSERT"
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
        # Kita gunakan executemany untuk efisiensi, 
        # meskipun batch-nya berisi update unik
        await db.executemany(query, device_data_batch)
        print(f"(DEVICE MONITOR) Updated status for {len(device_data_batch)} devices.")
    except Exception as e:
        print(f"Error during device UPSERT: {e}")