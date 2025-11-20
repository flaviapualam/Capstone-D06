# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
from db.postgresql import connect_to_db, close_db_connection, get_db_connection
import asyncio
from fastapi import Request

from services.email import check_smtp_async
from api.api_router import api_router
from mqtt.client import mqtt_listener_task, session_timeout_checker_task
from ml.tasks import periodic_training_task, periodic_prediction_task

mqtt_task = None
session_task = None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_task, session_task 
    
    pool = await connect_to_db()
    
    mqtt_task = asyncio.create_task(mqtt_listener_task(pool))
    session_task = asyncio.create_task(session_timeout_checker_task(pool)) # <-- Jalankan task timeout
    ml_training_task = asyncio.create_task(periodic_training_task(pool))
    # ml_prediction_task = asyncio.create_task(periodic_prediction_task(pool))

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

    if ml_training_task:
        ml_training_task.cancel()
        try: await ml_training_task
        except asyncio.CancelledError: print("ML training task successfully cancelled.")

    # if ml_prediction_task:
    #     ml_prediction_task.cancel()
    #     try: await ml_prediction_task
    #     except asyncio.CancelledError: print("ML prediction task successfully cancelled.")
 
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
    
    smtp_status = "error"
    smtp_message = ""
    
    try:
        # Panggil fungsi asinkron (yang menjalankan kode blocking di thread)
        smtp_is_ok = await check_smtp_async()
        if smtp_is_ok:
            smtp_status = "ok"
            smtp_message = "SMTP connection is healthy."
        else:
            smtp_message = "SMTP login or connection failed."
            
    except Exception as e:
        smtp_message = f"SMTP check failed: {str(e)}"

    final_status = "ok" if db_status == "ok" and smtp_status == "ok" else "error"
    if final_status == "error":
        raise HTTPException(
            status_code=503, 
            detail={
                "api_status": "error", 
                "db_status": db_status, 
                "smtp_status": smtp_status, 
                "message": f"DB: {db_message} | SMTP: {smtp_message}"
            }
        )

    return {
        "api_status": final_status, 
        "db_status": db_status, 
        "smtp_status": smtp_status,
        "message": "All critical services are healthy."
    }

app.include_router(api_router, prefix="")