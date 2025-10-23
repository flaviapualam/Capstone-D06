# app/api/v1/routes_auth.py
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth_schema import FarmerCreate, FarmerLogin, FarmerOut, Token
from app.services.auth_service import register_farmer, authenticate_farmer

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=FarmerOut, status_code=201)
async def register(farmer: FarmerCreate, db:AsyncSession = Depends(get_db)):
    return await register_farmer(db, farmer)

@router.post("/login", response_model=Token)
async def login(response: Response, farmer: FarmerLogin, db: AsyncSession = Depends(get_db)):
    token_data = await authenticate_farmer(db, farmer.email, farmer.password)
    response.set_cookie(
        key="access_token",
        value=token_data["access_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600*12,
    )
    return token_data