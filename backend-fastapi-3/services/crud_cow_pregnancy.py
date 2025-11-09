# services/crud_cow_pregnancy.py
import asyncpg
from uuid import UUID
from schemas.cow_pregnancy import CowPregnancyCreate, CowPregnancyUpdate

async def create_pregnancy(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    preg_in: CowPregnancyCreate
) -> asyncpg.Record:
    query = """
    INSERT INTO cow_pregnancy (cow_id, time_start)
    VALUES ($1, $2)
    RETURNING *;
    """
    new_preg = await db.fetchrow(query, cow_id, preg_in.time_start)
    return dict(new_preg)

async def get_pregnancy_by_id(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    pregnancy_id: int
) -> asyncpg.Record | None:
    """Mendapatkan satu rekaman untuk cek otorisasi/eksistensi"""
    query = "SELECT * FROM cow_pregnancy WHERE cow_id = $1 AND pregnancy_id = $2"
    record = await db.fetchrow(query, cow_id, pregnancy_id)
    return dict(record) if record else None

async def update_pregnancy(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    pregnancy_id: int, 
    preg_in: CowPregnancyUpdate
) -> asyncpg.Record | None:
    query = """
    UPDATE cow_pregnancy
    SET time_end = $1
    WHERE cow_id = $2 AND pregnancy_id = $3
    RETURNING *;
    """
    updated_preg = await db.fetchrow(
        query,
        preg_in.time_end,
        cow_id,
        pregnancy_id
    )
    return dict(updated_preg) if updated_preg else None

async def delete_pregnancy(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    pregnancy_id: int
) -> asyncpg.Record | None:
    query = "DELETE FROM cow_pregnancy WHERE cow_id = $1 AND pregnancy_id = $2 RETURNING *"
    deleted_preg = await db.fetchrow(query, cow_id, pregnancy_id)
    return dict(deleted_preg) if deleted_preg else None