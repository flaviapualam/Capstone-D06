# db/postgresql.py
import asyncpg
from core.config import settings
from typing import AsyncGenerator
from fastapi import HTTPException

# 'db_pool' akan menampung pool koneksi kita
db_pool: asyncpg.Pool = None

async def connect_to_db():
    """
    Membuat pool koneksi database saat startup.
    """
    global db_pool
    print("Connecting to database...")
    try:
        db_pool = await asyncpg.create_pool(
            settings.POSTGRE_URI,
            min_size=5,  # Koneksi minimal di pool
            max_size=20  # Koneksi maksimal di pool
        )
        print("Database connection pool established.")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        # Jika koneksi gagal saat startup, hentikan aplikasi
        raise

async def close_db_connection():
    """
    Menutup pool koneksi database saat shutdown.
    """
    global db_pool
    if db_pool:
        print("Closing database connection pool...")
        await db_pool.close()
        print("Database connection pool closed.")

async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency FastAPI untuk 'meminjam' koneksi dari pool.
    Ini akan dipanggil oleh setiap endpoint yang butuh akses DB.
    """
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection pool is not initialized")
    
    # 'acquire' meminjam koneksi dari pool
    async with db_pool.acquire() as connection:
        # 'yield' memberikan koneksi ini ke endpoint
        yield connection
        # Koneksi otomatis 'dirilis' (dikembalikan ke pool) 
        # setelah 'yield' selesai (baik sukses atau error)