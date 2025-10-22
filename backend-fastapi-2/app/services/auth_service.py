# app/services/auth_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.auth_farmer import Farmer 
from app.schemas.auth_schema import FarmerCreate
from app.core.security import hash_password, verify_password, create_access_token
from fastapi import HTTPException, status

async def register_farmer(db: AsyncSession, farmer: FarmerCreate):
    result = await db.execute(select(Farmer).where(Farmer.email == farmer.email))
    existing_farmer = result.scalar_one_or_none()
    if existing_farmer:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_farmer = Farmer(
        name=farmer.name,
        email=farmer.email,
        password_hash=hash_password(farmer.password)
    )

    db.add(new_farmer)
    await db.commit()
    await db.refresh(new_farmer)
    return new_farmer

async def authenticate_farmer(db: AsyncSession, email:str, password:str):
    result = await db.execute(select(Farmer).where(Farmer.email == email))
    farmer = result.scalar_one_or_none()
    if not farmer or not verify_password(password, farmer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token({"sub": str(farmer.farmer_id)})
    return {"access_token": access_token, "token_type": "bearer"}

