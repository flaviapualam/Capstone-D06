# api/endpoints/rfid.py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from schemas.rfid import RfidAssignRequest, RfidOwnershipResponse
from schemas.farmer import FarmerResponse
from services import crud_rfid, crud_cow # Impor crud_cow untuk cek kepemilikan
from db.postgresql import get_db_connection
from core.security import get_current_farmer
import asyncpg

router = APIRouter(
    prefix="/rfid",
    tags=["RFID Management"],
    dependencies=[Depends(get_current_farmer)] # Amankan semua rute
)

@router.post("/assign", response_model=RfidOwnershipResponse, status_code=status.HTTP_201_CREATED)
async def assign_rfid(
    assignment_request: RfidAssignRequest,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Menugaskan (atau memindahkan) RFID ke Sapi.
    Akan meng-nonaktifkan penugasan lama secara otomatis.
    """
    # 1. Otorisasi: Cek apakah Sapi ini milik Farmer yang login
    # (Kita panggil get_cow_by_id dari crud_cow, tapi tanpa join)
    query = "SELECT * FROM cow WHERE cow_id = $1"
    cow = await db.fetchrow(query, assignment_request.cow_id)
    
    if not cow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Sapi (cow_id) tidak ditemukan"
        )
    
    if cow['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Anda tidak punya hak akses ke sapi ini"
        )

    # 2. Eksekusi Transaksi
    new_assignment = await crud_rfid.assign_rfid_to_cow(
        db,
        rfid_id=assignment_request.rfid_id,
        cow_id=assignment_request.cow_id
    )
    
    if not new_assignment:
        # Ini bisa terjadi jika rfid_id tidak ada di tabel rfid_tag
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gagal menugaskan RFID. Pastikan RFID ID dan Cow ID valid."
        )

    return new_assignment