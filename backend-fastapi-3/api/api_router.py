# api/router.py
from fastapi import APIRouter
from api.endpoints import auth, cow, rfid, ml


api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(cow.router)
api_router.include_router(rfid.router)
api_router.include_router(ml.router)