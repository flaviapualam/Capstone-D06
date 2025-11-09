# db/postgresql.py
import asyncpg
from core.config import settings
from typing import AsyncGenerator
from fastapi import HTTPException

db_pool: asyncpg.Pool = None

async def connect_to_db() -> asyncpg.Pool:
    global db_pool
    print("Connecting to database...")
    try:
        pool = await asyncpg.create_pool(
            settings.POSTGRE_URI,
            min_size=5,
            max_size=20
        )
        print("Database connection pool established.")
        
        db_pool = pool
        return pool
        
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise

async def close_db_connection():
    global db_pool
    if db_pool:
        print("Closing database connection pool...")
        await db_pool.close()
        print("Database connection pool closed.")

async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection pool is not initialized")
    
    async with db_pool.acquire() as connection:
        yield connection