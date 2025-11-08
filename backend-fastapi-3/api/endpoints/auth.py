# api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.farmer import FarmerCreate, FarmerResponse
from services import authentication
from db.postgresql import get_db_connection
import asyncpg

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
    existing_farmer = await authentication.get_farmer_by_email(db, email=farmer_in.email)
    if existing_farmer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email has already registered",
        )
    
    new_farmer = await authentication.create_farmer(db, farmer=farmer_in)
    
    return new_farmer