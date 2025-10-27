# app/core/database.py
import asyncpg
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

postgres_pool = None
mongo_client = None
mongo_db = None

async def connect_to_postgres():
    global postgres_pool
    postgres_pool = await asyncpg.create_pool(dsn=settings.POSTGRE_URI)
    print("✅ PostgreSQL connected")

async def close_postgres():
    await postgres_pool.close()
    print("🔒 PostgreSQL connection closed")

async def get_postgres_conn():
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
