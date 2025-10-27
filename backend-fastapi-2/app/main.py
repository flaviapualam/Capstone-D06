# app/main.py
from fastapi import FastAPI
from app.core.database import (
    connect_to_postgres,
    close_postgres,
    connect_to_mongo,
    close_mongo_connection,
)
from app.api.v1 import routes_auth
from app.services.mqtt_service import start_mqtt
import asyncio

app = FastAPI(title="Backend Capstone D06")

mqtt_client = None

@app.on_event("startup")
async def startup():
    global mqtt_client
    print("🚀 Starting application...")

    # Connect databases
    await connect_to_postgres()
    await connect_to_mongo()

    # Start MQTT client in async event loop
    loop = asyncio.get_running_loop()
    mqtt_client = start_mqtt(loop)
    print("📡 MQTT client started")

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

# Register all routers
app.include_router(routes_auth.router)
