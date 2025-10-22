# app/api/v1/endpoints/status.py
from fastapi import APIRouter, Depends
from app.core.database import db_instance, get_pg_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter()

@router.get("/status", tags=["Status"])
async def server_status(pg: AsyncSession = Depends(get_pg_session)):
    mongo_status = "Disconnected"
    pg_status = "Disconnected"

    # MongoDB check
    try:
        await db_instance.db.command("ping")
        mongo_status = "Connected"
    except Exception as e:
        mongo_status = f"Error: {str(e)}"

    # PostgreSQL check
    try:
        await pg.execute(text("SELECT 1"))
        pg_status = "Connected"
    except Exception as e:
        pg_status = f"Error: {str(e)}"

    return {
        "status": "Active",
        "mongo": mongo_status,
        "postgres": pg_status
    }