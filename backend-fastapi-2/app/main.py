# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import (
    connect_to_postgres,
    close_postgres,
    connect_to_mongo,
    close_mongo_connection,
)
from app.api.v1 import routes_auth, routes_farm
from app.services.mqtt_service import start_mqtt
import asyncio

app = FastAPI(title="Backend Capstone D06")

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev server
    allow_credentials=True,  # Enable cookies
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

mqtt_client = None

@app.on_event("startup")
async def startup():
    global mqtt_client
    print("🚀 Starting application...")

    # Connect databases with error handling
    try:
        await connect_to_postgres()
    except Exception as e:
        print(f"⚠️  PostgreSQL connection failed: {e}")
        print("⚠️  API will start but database operations will fail")

    try:
        await connect_to_mongo()
    except Exception as e:
        print(f"⚠️  MongoDB connection failed: {e}")
        print("⚠️  API will start but MongoDB operations will fail")

    # Start MQTT client in async event loop
    try:
        loop = asyncio.get_running_loop()
        mqtt_client = start_mqtt(loop)
        print("📡 MQTT client started")
    except Exception as e:
        print(f"⚠️  MQTT client failed to start: {e}")
        print("⚠️  API will start but MQTT data ingestion will not work")

    print("✅ Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down application...")

    # Close databases
    await close_postgres()
    await close_mongo_connection()

    # Stop MQTT client if active
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("📴 MQTT client stopped")

# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "status": "healthy",
        "message": "Backend Capstone D06 API is running",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check including database connections.
    """
    from app.core.database import postgres_pool, mongo_db

    health = {
        "status": "healthy",
        "api": "running",
        "postgres": "connected" if postgres_pool else "disconnected",
        "mongodb": "connected" if mongo_db else "disconnected",
        "mqtt": "connected" if mqtt_client else "disconnected"
    }

    return health

# Register all routers
app.include_router(routes_auth.router)
app.include_router(routes_farm.router)
