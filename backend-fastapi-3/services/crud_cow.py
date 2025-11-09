# services/crud_cow.py
import asyncpg
from uuid import UUID
from schemas.cow import CowCreate, CowUpdate
import json

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
) -> list:
    """
    Mengambil semua sapi milik farmer,
    dengan data kehamilan digabung sebagai array JSON.
    """
    query = """
    SELECT 
        c.*, 
        COALESCE(
            json_agg(cp.*) FILTER (WHERE cp.pregnancy_id IS NOT NULL), 
            '[]'::json
        ) as pregnancies
    FROM cow c
    LEFT JOIN cow_pregnancy cp ON c.cow_id = cp.cow_id
    WHERE c.farmer_id = $1
    GROUP BY c.cow_id
    ORDER BY c.name;
    """
    cows = await db.fetch(query, farmer_id)
    
    # --- 2. Lakukan perulangan dan parsing ---
    results = []
    for cow_record in cows:
        cow_dict = dict(cow_record)
        # 'pregnancies' saat ini adalah string (misal: '[{...}]' atau '[]')
        # Kita ubah menjadi list Python
        cow_dict['pregnancies'] = json.loads(cow_dict['pregnancies'])
        results.append(cow_dict)
        
    return results

async def get_cow_by_id(
    db: asyncpg.Connection, 
    cow_id: UUID
) -> dict | None:
    """
    Mengambil satu sapi,
    dengan data kehamilan digabung sebagai array JSON.
    """
    query = """
    SELECT 
        c.*, 
        COALESCE(
            json_agg(cp.*) FILTER (WHERE cp.pregnancy_id IS NOT NULL), 
            '[]'::json
        ) as pregnancies
    FROM cow c
    LEFT JOIN cow_pregnancy cp ON c.cow_id = cp.cow_id
    WHERE c.cow_id = $1
    GROUP BY c.cow_id;
    """
    cow = await db.fetchrow(query, cow_id)
    
    if not cow:
        return None
        
    # --- 3. Ubah record dan parsing ---
    cow_dict = dict(cow)
    # 'pregnancies' saat ini adalah string, ubah menjadi list
    cow_dict['pregnancies'] = json.loads(cow_dict['pregnancies'])
    
    return cow_dict

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
    return dict(deleted_cow)