# schemas/cow.py
from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Literal

from schemas.cow_pregnancy import CowPregnancyResponse

class CowBase(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    gender: Literal['MALE', 'FEMALE'] | None = None

class CowCreate(CowBase):
    name: str

class CowUpdate(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    gender: Literal['MALE', 'FEMALE'] | None = None

class CowResponse(CowBase):
    cow_id: UUID
    farmer_id: UUID
    pregnancies: list[CowPregnancyResponse] = []

    class Config:
        from_attributes = True

