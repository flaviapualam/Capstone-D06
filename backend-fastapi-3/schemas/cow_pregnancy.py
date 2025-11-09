# schemas/cow_pregnancy.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class CowPregnancyBase(BaseModel):
    time_start: datetime
    time_end: datetime | None = None

class CowPregnancyCreate(BaseModel):
    """Skema untuk mencatat kehamilan baru (Input)"""
    time_start: datetime

class CowPregnancyUpdate(BaseModel):
    """Skema untuk memperbarui kehamilan (Input), misal: mencatat time_end"""
    time_end: datetime

class CowPregnancyResponse(CowPregnancyBase):
    """Skema untuk menampilkan data kehamilan (Output)"""
    pregnancy_id: int
    cow_id: UUID

    class Config:
        from_attributes = True