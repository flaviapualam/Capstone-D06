# api/endpoints/cows.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta

from schemas.cow import CowCreate, CowUpdate, CowResponse
from schemas.farmer import FarmerResponse
from schemas.cow_pregnancy import (
    CowPregnancyCreate, 
    CowPregnancyUpdate, 
    CowPregnancyResponse
)
from schemas.sensor import SensorDataPoint
from services import crud_cow, crud_cow_pregnancy, crud_sensor
from services.crud_session import (
    get_eating_sessions,
    get_daily_summary,
    get_weekly_summary,
    get_sessions_for_date
)
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

@router.get(
    "/{cow_id}/sensor_history", 
    response_model=List[SensorDataPoint],
    tags=["Sensor History"] # Tag terpisah di Swagger
)
async def get_cow_sensor_history(
    # 1. Validasi kepemilikan sapi (otomatis)
    cow: dict = Depends(get_cow_and_verify_ownership),
    # 2. Ambil parameter query (misal: /sensor_history?hours=2)
    #    Defaultnya adalah 24 jam terakhir. Max 720 jam (30 hari)
    hours: int = Query(default=24, ge=1, le=720), 
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Mengambil data sensor mentah (historis) untuk seekor sapi.
    Berguna untuk mengisi grafik di frontend sebelum SSE dimulai.
    Max: 720 jam (30 hari), Default: 24 jam
    """
    # 3. Tentukan rentang waktu
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 4. Panggil service untuk mengambil data
    history = await crud_sensor.get_sensor_history(
        db, 
        cow_id=cow['cow_id'], 
        start_time=start_time, 
        end_time=end_time
    )
    
    return history

@router.get(
    "/{cow_id}/eating-sessions",
    tags=["Eating Sessions"]
)
async def get_cow_eating_sessions(
    cow: dict = Depends(get_cow_and_verify_ownership),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Get eating sessions for a cow"""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    sessions = await get_eating_sessions(db, cow['cow_id'], start, end)
    return {"sessions": sessions}

@router.get(
    "/{cow_id}/daily-summary",
    tags=["Eating Sessions"]
)
async def get_cow_daily_summary(
    cow: dict = Depends(get_cow_and_verify_ownership),
    days: int = Query(default=7, ge=1, le=30),
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Get daily eating summary for a cow"""
    summary = await get_daily_summary(db, cow['cow_id'], days)
    
    # Get sessions for each day
    for day in summary:
        day['sessions'] = await get_sessions_for_date(
            db, 
            cow['cow_id'], 
            day['date'].isoformat()
        )
    
    return {"daily_summaries": summary}

@router.get(
    "/{cow_id}/weekly-summary",
    tags=["Eating Sessions"]
)
async def get_cow_weekly_summary(
    cow: dict = Depends(get_cow_and_verify_ownership),
    weeks: int = Query(default=2, ge=1, le=8),
    db: asyncpg.Connection = Depends(get_db_connection)
):
    """Get weekly eating summary for a cow (current week + previous week)"""
    summary = await get_weekly_summary(db, cow['cow_id'], weeks)
    
    # Get daily summaries for each week
    for week in summary:
        # Get days between week_start and week_end
        week_days = await db.fetch("""
            SELECT 
                date,
                total_sessions,
                total_eat_duration,
                total_feed_weight,
                avg_temperature,
                anomaly_count
            FROM daily_eating_summary
            WHERE cow_id = $1
            AND date BETWEEN $2 AND $3
            ORDER BY date ASC
        """, cow['cow_id'], week['week_start'], week['week_end'])
        
        week['daily_summaries'] = [dict(d) for d in week_days]
        
        # Get sessions for each day
        for day in week['daily_summaries']:
            day['sessions'] = await get_sessions_for_date(
                db,
                cow['cow_id'],
                day['date'].isoformat()
            )
    
    return {
        "current_week": summary[0] if len(summary) > 0 else None,
        "previous_week": summary[1] if len(summary) > 1 else None
    }