# services/crud_sensor.py
import asyncpg
from typing import List, Tuple
from uuid import UUID
from datetime import datetime


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

async def get_sensor_history(
    db: asyncpg.Connection, 
    cow_id: UUID,
    start_time: datetime,
    end_time: datetime
) -> List[dict]:
    """
    Mengambil data sensor mentah untuk satu Sapi dalam rentang waktu.
    
    Query ini melakukan JOIN untuk menemukan semua RFID yang
    PERNAH ditugaskan ke sapi ini, lalu mengambil data sensor
    selama RFID itu aktif.
    """
    query = """
    SELECT 
        t1."timestamp", t1.device_id, t1.rfid_id, 
        t1.weight, t1.temperature_c, t1.ip
    FROM output_sensor AS t1
    INNER JOIN rfid_ownership AS t2
        -- 1. Gabungkan berdasarkan rfid_id
        ON t1.rfid_id = t2.rfid_id 
        -- 2. Pastikan data sensor ini milik sapi yang benar
        AND t2.cow_id = $1
        -- 3. Pastikan data sensor diambil SELAMA RFID itu aktif
        AND t1."timestamp" >= t2.time_start 
        AND (t1."timestamp" <= t2.time_end OR t2.time_end IS NULL)
    WHERE 
        -- 4. Filter berdasarkan rentang waktu yang diminta
        t1."timestamp" BETWEEN $2 AND $3
    ORDER BY t1."timestamp" DESC
    LIMIT 1000; -- Batasi agar tidak overload (opsional tapi disarankan)
    """
    
    try:
        records = await db.fetch(query, cow_id, start_time, end_time)
        # Konversi asyncpg.Record menjadi dict
        return [dict(record) for record in records]
    except Exception as e:
        print(f"Error getting sensor history: {e}")
        return []