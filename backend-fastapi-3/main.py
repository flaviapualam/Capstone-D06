# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
from db.postgresql import connect_to_db, close_db_connection, get_db_connection
import asyncio
from fastapi import Request

from api.api_router import api_router
from mqtt.client import mqtt_listener_task, session_timeout_checker_task

mqtt_task = None
session_task = None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_task, session_task 
    
    pool = await connect_to_db()
    
    mqtt_task = asyncio.create_task(mqtt_listener_task(pool))
    session_task = asyncio.create_task(session_timeout_checker_task(pool)) # <-- Jalankan task timeout
    
    yield
    
    if mqtt_task:
        mqtt_task.cancel()
        try:
            await mqtt_task
        except asyncio.CancelledError:
            print("MQTT listener task successfully cancelled.")
            
    if session_task:
        session_task.cancel()
        try:
            await session_task
        except asyncio.CancelledError:
            print("Session timeout checker task successfully cancelled.")
            
    await close_db_connection()

app = FastAPI(
    title="Backend Capstone D06 v3",
    lifespan=lifespan
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.10:3000",
    "http://103.181.161.143:3000",
    "http://103.181.161.143",
    "https://103.181.161.143",
    "https://project-capstone.my.id"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
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

# @app.options("/{path:path}")
# async def preflight_handler(path: str, request: Request):
#     return {}

app.include_router(api_router, prefix="")