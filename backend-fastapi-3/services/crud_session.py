# services/crud_session.py
import asyncpg
from uuid import UUID
from datetime import datetime, timedelta, date
from typing import List, Optional

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
        return None

    query = """
    INSERT INTO eat_session (
        device_id, rfid_id, cow_id, 
        time_start, time_end, 
        weight_start, weight_end,
        average_temp
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING session_id;
    """
    try:
        session_id = await db.fetchval(
            query, 
            device_id, rfid_id, cow_id, 
            time_start, time_end, 
            weight_start, weight_end,
            average_temp
        )
        print(f"(SESSION CREATED) Cow {cow_id} at {device_id} finished. Avg Temp: {average_temp:.2f}")
        return session_id
    except Exception as e:
        print(f"Error creating eat_session: {e}")

async def get_eating_sessions(
    conn: asyncpg.Connection,
    cow_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[dict]:
    """Get eating sessions for a cow from view"""
    query = """
        SELECT 
            session_id,
            timestamp,
            eat_duration,
            feed_weight,
            eat_speed,
            temperature,
            is_anomaly
        FROM eating_session_detail
        WHERE cow_id = $1
    """
    params = [cow_id]
    
    if start_date:
        query += " AND timestamp >= $2"
        params.append(start_date)
    
    if end_date:
        query += f" AND timestamp <= ${len(params) + 1}"
        params.append(end_date)
    
    query += " ORDER BY timestamp DESC"
    
    rows = await conn.fetch(query, *params)
    return [dict(row) for row in rows]

async def get_daily_summary(
    conn: asyncpg.Connection,
    cow_id: UUID,
    days: int = 7
) -> List[dict]:
    """Get daily summary for a cow"""
    query = """
        SELECT 
            date,
            total_sessions,
            total_eat_duration,
            total_feed_weight,
            avg_temperature,
            anomaly_count
        FROM daily_eating_summary
        WHERE cow_id = $1
        -- KOREKSI DENGAN INTERVAL EXPLISIT: CURRENT_DATE - (jumlah hari * 1 hari)
        AND date >= CURRENT_DATE - ($2 * INTERVAL '1 day') 
        ORDER BY date ASC
    """
    rows = await conn.fetch(query, cow_id, days)
    return [dict(row) for row in rows]

async def get_weekly_summary(
    conn: asyncpg.Connection,
    cow_id: UUID,
    weeks: int = 4
) -> List[dict]:
    """Get weekly summary for a cow"""
    query = """
        SELECT 
            week_start,
            week_end,
            total_sessions,
            total_eat_duration,
            total_feed_weight,
            avg_temperature,
            anomaly_count
        FROM weekly_eating_summary
        WHERE cow_id = $1
        -- KOREKSI DENGAN INTERVAL EXPLISIT: CURRENT_DATE - (jumlah minggu * 7 hari)
        AND week_start >= CURRENT_DATE - ($2 * INTERVAL '7 days') 
        ORDER BY week_start DESC
    """
    rows = await conn.fetch(query, cow_id, weeks)
    return [dict(row) for row in rows]

async def get_sessions_for_date(
    conn: asyncpg.Connection,
    cow_id: UUID,
    date_str: str # Renamed parameter for clarity
) -> List[dict]:
    """Get all sessions for a specific date"""    
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"Invalid date format received: {date_str}")
        return []

    query = """
        SELECT 
            session_id,
            timestamp,
            eat_duration,
            feed_weight,
            eat_speed,
            temperature,
            is_anomaly
        FROM eating_session_detail
        WHERE cow_id = $1
        AND DATE(timestamp) = $2 
        ORDER BY timestamp ASC
    """
    rows = await conn.fetch(query, cow_id, query_date) 
    return [dict(row) for row in rows]