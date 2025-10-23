# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

Base = declarative_base()

engine = create_async_engine(settings.POSTGRE_URI, echo= True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        yield session

mongo_client = None
mongo_db = None

async def connect_to_mongo():
    global mongo_client, mongo_db
    mongo_client= AsyncIOMotorClient(settings.MONGO_URI)
    mongo_db = mongo_client[settings.MONGO_DB]
    print(f"Mongodb connetion scces")

async def close_mongo_connection():
    mongo_client.close()