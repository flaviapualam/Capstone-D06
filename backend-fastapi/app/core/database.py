# app/core/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


# -----------------
# MongoDB
# -----------------
class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_instance.db = db_instance.client[settings.MONGODB_DB]
    print("Connected to MongoDB")

async def close_mongo_connection():
    db_instance.client.close()
    print("MongoDB connection is closed")

# -----------------
# PostgreSQL
# -----------------
Base = declarative_base()

engine = create_async_engine(
    settings.POSTGRES_URI, 
    echo=True, 
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_pg_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def connect_to_postgres():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        print(" Connected to PostgreSQL")
    except Exception as e:
        print(f" PostgreSQL connection error: {e}")

async def close_postgres_connection():
    await engine.dispose()
    print(" PostgreSQL connection closed")