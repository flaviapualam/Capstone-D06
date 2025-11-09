# api/endpoints/cows.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from schemas.cow import CowCreate, CowUpdate, CowResponse
from schemas.farmer import FarmerResponse
from services import crud_cow
from db.postgresql import get_db_connection
from core.security import get_current_farmer
import asyncpg

router = APIRouter(
    prefix="/cow",
    tags=["Cows"],
    dependencies=[Depends(get_current_farmer)] # Amankan SEMUA rute di file ini dengan 'get_current_farmer'
)

@router.post("/", response_model=CowResponse, status_code=status.HTTP_201_CREATED)
async def create_new_cow(
    cow_in: CowCreate,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Membuat Sapi baru untuk farmer yang sedang login.
    """
    new_cow = await crud_cow.create_cow(
        db, cow=cow_in, farmer_id=current_farmer.farmer_id
    )
    return new_cow

#--------------------
# READ (Membaca Semua)
#--------------------
@router.get("/", response_model=List[CowResponse])
async def read_my_cows(
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Mengambil semua Sapi yang dimiliki oleh farmer yang sedang login.
    """
    cows = await crud_cow.get_cows_by_farmer(db, farmer_id=current_farmer.farmer_id)
    return cows

#--------------------
# READ (Membaca Satu)
#--------------------
@router.get("/{cow_id}", response_model=CowResponse)
async def read_cow(
    cow_id: UUID,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Mengambil satu Sapi berdasarkan ID.
    Hanya mengizinkan jika Sapi itu milik farmer yang login.
    """
    cow = await crud_cow.get_cow_by_id(db, cow_id=cow_id)
    
    # 404 - Not Found
    if not cow:
        raise HTTPException(status_code=404, detail="Sapi tidak ditemukan")
        
    # 403 - Forbidden (Otorisasi Gagal)
    if cow['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(status_code=403, detail="Anda tidak punya hak akses ke sapi ini")
        
    return cow

#--------------------
# UPDATE (Memperbarui)
#--------------------
@router.patch("/{cow_id}", response_model=CowResponse)
async def update_existing_cow(
    cow_id: UUID,
    cow_in: CowUpdate,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Memperbarui Sapi. Hanya mengizinkan jika Sapi itu milik farmer yang login.
    """
    # Pertama, cek kepemilikan (sama seperti read_cow)
    cow = await crud_cow.get_cow_by_id(db, cow_id=cow_id)
    if not cow:
        raise HTTPException(status_code=404, detail="Sapi tidak ditemukan")
    if cow['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(status_code=403, detail="Anda tidak punya hak akses ke sapi ini")
        
    # Jika lolos cek, baru lakukan update
    updated_cow = await crud_cow.update_cow(db, cow_id=cow_id, cow=cow_in)
    return updated_cow

#--------------------
# DELETE (Menghapus)
#--------------------
@router.delete("/{cow_id}", response_model=CowResponse)
async def delete_existing_cow(
    cow_id: UUID,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Menghapus Sapi. Hanya mengizinkan jika Sapi itu milik farmer yang login.
    """
    # Cek kepemilikan (sama seperti read_cow)
    cow = await crud_cow.get_cow_by_id(db, cow_id=cow_id)
    if not cow:
        raise HTTPException(status_code=404, detail="Sapi tidak ditemukan")
    if cow['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(status_code=403, detail="Anda tidak punya hak akses ke sapi ini")

    # Jika lolos cek, baru lakukan delete
    deleted_cow = await crud_cow.delete_cow(db, cow_id=cow_id)
    return deleted_cow