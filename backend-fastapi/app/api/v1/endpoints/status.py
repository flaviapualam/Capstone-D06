from fastapi import APIRouter
from app.core.database import db_instance

router = APIRouter()

@router.get("/status", tags=["Status"])
async def server_status():
    mongo_status = "Disconnected"

    try:
        # run a simple command to check DB
        await db_instance.db.command("ping")
        mongo_status = "Connected"
    except Exception as e:
        mongo_status = f"Error: {str(e)}"

    return {
        "status": "Active",
        "mongo": mongo_status
    }
