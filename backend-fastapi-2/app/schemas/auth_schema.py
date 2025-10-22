# app/schemas/auth_schema.py
from pydantic import BaseModel, EmailStr

class FarmerBase(BaseModel):
    name: str
    email: EmailStr

class FarmerCreate(FarmerBase):
    password:str

class FarmerLogin(BaseModel):
    email: EmailStr
    password: str 

class FarmerOut(FarmerBase):
    farmer_id:str

    class Config:
        orm_mode = True 

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    