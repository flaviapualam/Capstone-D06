# api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, Response
from schemas.farmer import FarmerCreate, FarmerResponse, FarmerLogin
from schemas.token import Token
from services import authentication
from db.postgresql import get_db_connection
from core.security import (
    create_access_token,
    verify_password,
    get_current_farmer
)
import asyncpg
from core.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post(
    "/register", 
    response_model=FarmerResponse, 
    status_code=status.HTTP_201_CREATED
)
async def register_farmer(
    farmer_in: FarmerCreate,
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Register farmer in database.
    """
    existing_farmer = await authentication.get_farmer_by_email(db, email=farmer_in.email)
    if existing_farmer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email has already registered",
        )
    
    new_farmer = await authentication.create_farmer(db, farmer=farmer_in)

    return new_farmer

@router.post("/login", response_model=Token)
async def login_farmer(
    response: Response, 
    login_request: FarmerLogin = Body(...), 
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Give access to farmer using app.
    """
    farmer_record = await authentication.get_farmer_by_email(
        db, email=login_request.email
    )
    if not farmer_record or not verify_password(
        login_request.password, farmer_record['password_hash']
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
        )
    token_data = {
        "sub": farmer_record['email'], 
        "farmer_id": str(farmer_record['farmer_id'])
    }
    access_token = create_access_token(data=token_data)

    response.set_cookie(
        key="access_token", # Nama cookie
        value=f"Bearer {access_token}", 
        httponly=True,      
        secure=False,        
        samesite="none",  
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 
    )
    
    return {"status": "success", "message": "Logged in successfully"}


@router.get("/me", response_model=FarmerResponse)
async def check_cookies(
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Get data farmer who is log in. Use to check is token works.
    """
    return current_farmer