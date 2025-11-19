# services/crud_session.py
import asyncpg
from uuid import UUID
from datetime import datetime

async def get_active_cow_by_rfid(db: asyncpg.Connection, rfid_id: str) -> UUID | None:
    if not rfid_id:
        return None
    query = "SELECT cow_id FROM rfid_ownership WHERE rfid_id = $1 AND time_end IS NULL;"
    record = await db.fetchrow(query, rfid_id)
    return record['cow_id'] if record else None

async def create_eat_session(
    db: asyncpg.Connection,
    device_id: str,
    rfid_id: str,
    cow_id: UUID,
    time_start: datetime,
    time_end: datetime,
    weight_start: float,
    weight_end: float,
    average_temp: float
):
    if weight_end >= weight_start:
        print(f"(SESSION CANCELED) Sesi {device_id} dibatalkan (berat tidak berkurang).")
        return

    query = """
    INSERT INTO eat_session (
        device_id, rfid_id, cow_id, 
        time_start, time_end, 
        weight_start, weight_end,
        average_temp
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
    """
    try:
        await db.execute(
            query, 
            device_id, rfid_id, cow_id, 
            time_start, time_end, 
            weight_start, weight_end,
            average_temp
        )
        print(f"(SESSION CREATED) Cow {cow_id} at {device_id} finished. Avg Temp: {average_temp:.2f}")
    except Exception as e:
        print(f"Error creating eat_session: {e}")