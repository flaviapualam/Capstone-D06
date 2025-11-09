# services/crud_cow.py
import asyncpg
from uuid import UUID
from schemas.cow import CowCreate, CowUpdate

async def create_cow(
    db: asyncpg.Connection, 
    cow: CowCreate, 
    farmer_id: UUID
) -> asyncpg.Record:
    """
    Add new cow into a farmer.
    """
    query = """
    INSERT INTO cow (farmer_id, name, date_of_birth, gender)
    VALUES ($1, $2, $3, $4)
    RETURNING *;
    """
    new_cow = await db.fetchrow(
        query,
        farmer_id,
        cow.name,
        cow.date_of_birth,
        cow.gender
    )
    return dict(new_cow)

async def get_cows_by_farmer(
    db: asyncpg.Connection, 
    farmer_id: UUID
) -> list[asyncpg.Record]:
    """
    Get all cows from a farmer
    """
    query = "SELECT * FROM cow WHERE farmer_id = $1 ORDER BY name"
    cows = await db.fetch(query, farmer_id)
    return [dict(cow) for cow in cows]

async def get_cow_by_id(
    db: asyncpg.Connection, 
    cow_id: UUID
) -> asyncpg.Record | None:
    """
    Get a cow by cow id.
    """
    query = "SELECT * FROM cow WHERE cow_id = $1"
    cow = await db.fetchrow(query, cow_id)
    return dict(cow)

async def update_cow(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    cow: CowUpdate
) -> asyncpg.Record | None:
    """
    Update a cow. 
    using COALESCE for partially update (PATCH).
    """
    query = """
    UPDATE cow
    SET
        name = COALESCE($1, name),
        date_of_birth = COALESCE($2, date_of_birth),
        gender = COALESCE($3, gender)
    WHERE cow_id = $4
    RETURNING *;
    """
    updated_cow = await db.fetchrow(
        query,
        cow.name,
        cow.date_of_birth,
        cow.gender,
        cow_id
    )
    return dict(updated_cow)

async def delete_cow(
    db: asyncpg.Connection, 
    cow_id: UUID
) -> asyncpg.Record | None:
    """
    Remove a cow using its id.
    """
    query = "DELETE FROM cow WHERE cow_id = $1 RETURNING *"
    deleted_cow = await db.fetchrow(query, cow_id)
    return deleted_cow