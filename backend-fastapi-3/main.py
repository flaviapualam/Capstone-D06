# main.py
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import asyncpg
from db.postgresql import connect_to_db, close_db_connection, get_db_connection

from api.api_router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    yield
    await close_db_connection()

app = FastAPI(
    title="Backend Capstone D06 v3",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"status": "Backend Capstone D06 v3 is running"}

@app.get("/health", tags=["Status"])
async def health_check(
    db: asyncpg.Connection = Depends(get_db_connection)
):
    db_status = "error"
    db_message = ""
    
    try:
        result = await db.fetchval("SELECT 1")
        
        if result == 1:
            db_status = "ok"
            db_message = "Database connection is healthy."
        else:
            db_message = "Database connection is unhealthy (query failed)."
            
    except Exception as e:
        db_message = f"Database connection failed: {str(e)}"

    if db_status == "error":
        raise HTTPException(
            status_code=503, 
            detail={"api_status": "ok", "db_status": db_status, "message": db_message}
        )

    return {"api_status": "ok", "db_status": db_status, "message": db_message}

app.include_router(api_router, prefix="/api/v1")