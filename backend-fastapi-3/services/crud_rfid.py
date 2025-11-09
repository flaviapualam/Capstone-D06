# services/crud_rfid.py
import asyncpg
from typing import List, Tuple

async def upsert_rfid_tags(db: asyncpg.Connection, rfid_batch: List[Tuple]):
    query = """
    INSERT INTO rfid_tag (rfid_id, created_at)
    VALUES ($1, NOW())
    ON CONFLICT (rfid_id) DO NOTHING;
    """
    try:
        await db.executemany(query, rfid_batch)
        print(f"(RFID REGISTER) Processed {len(rfid_batch)} RFID tags.")
    except Exception as e:
        print(f"Error during RFID tag UPSERT: {e}")