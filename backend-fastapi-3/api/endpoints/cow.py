# api/endpoints/cows.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from schemas.cow import CowCreate, CowUpdate, CowResponse
from schemas.farmer import FarmerResponse
# --- IMPOR BARU ---
from schemas.cow_pregnancy import (
    CowPregnancyCreate, 
    CowPregnancyUpdate, 
    CowPregnancyResponse
)
from services import crud_cow, crud_cow_pregnancy 
from db.postgresql import get_db_connection
from core.security import get_current_farmer
import asyncpg

router = APIRouter(
    prefix="/cow", # Prefix Anda "/cow", bukan "/cows"
    tags=["Cows"],
    dependencies=[Depends(get_current_farmer)]
)

async def get_cow_and_verify_ownership(
    cow_id: UUID,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
) -> dict:
    """
    Dependency yang mengambil data sapi dan memverifikasi farmer
    yang login adalah pemiliknya.
    """
    cow = await crud_cow.get_cow_by_id(db, cow_id=cow_id) 
    
    if not cow:
        raise HTTPException(status_code=404, detail="Sapi tidak ditemukan")
    if cow['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(status_code=403, detail="Anda tidak punya hak akses ke sapi ini")
    return cow

@router.post("/", response_model=CowResponse, status_code=status.HTTP_201_CREATED)
async def create_new_cow(
    cow_in: CowCreate,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    new_cow = await crud_cow.create_cow(
        db, cow=cow_in, farmer_id=current_farmer.farmer_id
    )
    cow_data = await crud_cow.get_cow_by_id(db, new_cow['cow_id'])
    return cow_data

@router.get("/", response_model=List[CowResponse])
async def read_my_cows(
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    cows = await crud_cow.get_cows_by_farmer(db, farmer_id=current_farmer.farmer_id)
    return cows

@router.get("/{cow_id}", response_model=CowResponse)
async def read_cow(
    cow: dict = Depends(get_cow_and_verify_ownership)
):
    return cow

@router.patch("/{cow_id}", response_model=CowResponse)
async def update_existing_cow(
    cow_id: UUID, # Kita butuh ID untuk 'update_cow'
    cow_in: CowUpdate,
    cow: dict = Depends(get_cow_and_verify_ownership), # Verifikasi
    db: asyncpg.Connection = Depends(get_db_connection)
):
    await crud_cow.update_cow(db, cow_id=cow_id, cow=cow_in)
    updated_cow_data = await crud_cow.get_cow_by_id(db, cow_id=cow_id)
    return updated_cow_data

@router.delete("/{cow_id}", response_model=CowResponse)
async def delete_existing_cow(
    cow_id: UUID,
    cow: dict = Depends(get_cow_and_verify_ownership), # Verifikasi
    db: asyncpg.Connection = Depends(get_db_connection)
):
    deleted_cow = await crud_cow.delete_cow(db, cow_id=cow_id)
    return deleted_cow

@router.post(
    "/{cow_id}/pregnancies", 
    response_model=CowPregnancyResponse, 
    status_code=status.HTTP_201_CREATED,
)
async def add_pregnancy_record(
    preg_in: CowPregnancyCreate,
    cow: dict = Depends(get_cow_and_verify_ownership), # Verifikasi kepemilikan sapi
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Mencatat kehamilan baru untuk sapi yang spesifik."""
    new_record = await crud_cow_pregnancy.create_pregnancy(
        db, cow_id=cow['cow_id'], preg_in=preg_in
    )
    return new_record

@router.patch(
    "/{cow_id}/pregnancies/{pregnancy_id}", 
    response_model=CowPregnancyResponse,
)
async def update_pregnancy_record(
    pregnancy_id: int,
    preg_in: CowPregnancyUpdate,
    cow: dict = Depends(get_cow_and_verify_ownership), # Verifikasi kepemilikan sapi
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Memperbarui satu rekaman kehamilan (misal: mencatat time_end)."""
    updated_record = await crud_cow_pregnancy.update_pregnancy(
        db, 
        cow_id=cow['cow_id'], 
        pregnancy_id=pregnancy_id, 
        preg_in=preg_in
    )
    if not updated_record:
        raise HTTPException(status_code=404, detail="Rekaman kehamilan tidak ditemukan")
    return updated_record

@router.delete(
    "/{cow_id}/pregnancies/{pregnancy_id}", 
    response_model=CowPregnancyResponse,
)
async def delete_pregnancy_record(
    pregnancy_id: int,
    cow: dict = Depends(get_cow_and_verify_ownership), # Verifikasi kepemilikan sapi
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Menghapus satu rekaman kehamilan (misal: salah input)."""
    deleted_record = await crud_cow_pregnancy.delete_pregnancy(
        db, cow_id=cow['cow_id'], pregnancy_id=pregnancy_id
    )
    if not deleted_record:
        raise HTTPException(status_code=404, detail="Rekaman kehamilan tidak ditemukan")
    return deleted_record