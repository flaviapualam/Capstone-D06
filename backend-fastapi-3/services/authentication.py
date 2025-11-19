
import asyncpg
from schemas.farmer import FarmerCreate
from core.security import get_password_hash
from uuid import UUID
from typing import Optional # Digunakan untuk tipe kembalian yang lebih jelas

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

async def get_farmer_email_by_id(db: asyncpg.Connection, farmer_id: UUID) -> str | None:
    """
    Mengambil alamat email dari tabel farmer berdasarkan farmer_id.
    
    Args:
        db: Koneksi asyncpg dari connection pool.
        farmer_id: UUID dari farmer yang dicari.
        
    Returns:
        Alamat email (str) atau None jika farmer tidak ditemukan.
    """
    query = "SELECT email FROM farmer WHERE farmer_id = $1"
    
    # fetchval adalah cara paling efisien untuk mengambil satu nilai (kolom)
    email = await db.fetchval(query, farmer_id)
    
    return email