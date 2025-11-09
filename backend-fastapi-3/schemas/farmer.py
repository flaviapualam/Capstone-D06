# schemas/farmer.py
from pydantic import BaseModel, EmailStr, constr
from uuid import UUID
from datetime import datetime

class FarmerBase(BaseModel):
    name: str
    email: EmailStr

class FarmerCreate(FarmerBase):
    password: constr(min_length=8, max_length=72) 

class FarmerResponse(FarmerBase):
    farmer_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True # Mengizinkan Pydantic membaca dari objek DB

class FarmerLogin(BaseModel):
    """
    Skema yang digunakan HANYA untuk body request login.
    """
    email: EmailStr
    password: str