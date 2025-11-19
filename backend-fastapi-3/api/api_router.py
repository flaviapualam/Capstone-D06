# api/router.py
from fastapi import APIRouter
from api.endpoints import auth, cow, rfid, ml, streaming, system

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(cow.router)
api_router.include_router(rfid.router)
api_router.include_router(ml.router)
api_router.include_router(streaming.router)
# api_router.include_router(system.router)