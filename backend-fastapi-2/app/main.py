# app/main.py
from fastapi import FastAPI
from app.core.database import engine, Base, connect_to_mongo, close_mongo_connection
from app.api.v1 import routes_auth
from app.services.mqtt_service import start_mqtt
import asyncio

app = FastAPI(title="Backend Capstone")

mqtt_client = None

@app.on_event("startup")
async def startup():
    global mqtt_client
    print("🚀 Starting application...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await connect_to_mongo()
    loop = asyncio.get_running_loop()
    mqtt_client = start_mqtt(loop)

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down application...")
    await close_mongo_connection()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


app.include_router(routes_auth.router)