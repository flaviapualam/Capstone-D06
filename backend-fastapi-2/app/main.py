# app/main.py
from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.v1 import routes_auth

app = FastAPI(title="Backend Capstone")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(routes_auth.router)