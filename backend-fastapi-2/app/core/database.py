# app/core/database.py
import asyncpg
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException

postgres_pool = None
mongo_client = None
mongo_db = None

async def connect_to_postgres():
    global postgres_pool
    try:
        postgres_pool = await asyncpg.create_pool(dsn=settings.POSTGRE_URI)
        print("✅ PostgreSQL connected")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        postgres_pool = None
        raise

async def close_postgres():
    if postgres_pool:
        await postgres_pool.close()
        print("🔒 PostgreSQL connection closed")

async def get_postgres_conn():
    if postgres_pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database not connected. Please check database configuration and ensure PostgreSQL is running."
        )
    async with postgres_pool.acquire() as connection:
        yield connection

async def connect_to_mongo():
    global mongo_client, mongo_db
    mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
    mongo_db = mongo_client[settings.MONGO_DB]
    print("✅ MongoDB connected")

async def close_mongo_connection():
    mongo_client.close()
    print("🔒 MongoDB connection closed")

def get_mongo_db():
    return mongo_db
