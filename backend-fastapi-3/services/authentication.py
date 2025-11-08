
import asyncpg
from schemas.farmer import FarmerCreate
from core.security import get_password_hash
from uuid import UUID

async def get_farmer_by_email(db: asyncpg.Connection, email: str) -> asyncpg.Record | None:
    query = "SELECT * FROM farmer WHERE email = $1"
    return await db.fetchrow(query, email)

async def create_farmer(db: asyncpg.Connection, farmer: FarmerCreate) -> asyncpg.Record:
    hashed_password = get_password_hash(farmer.password)
    
    query = """
    INSERT INTO farmer (name, email, password_hash)
    VALUES ($1, $2, $3)
    RETURNING farmer_id, name, email, created_at;
    """
    
    try:
        new_farmer_record = await db.fetchrow(
            query,
            farmer.name,
            farmer.email,
            hashed_password
        )
        return dict(new_farmer_record)
    except asyncpg.exceptions.UniqueViolationError:
        return None