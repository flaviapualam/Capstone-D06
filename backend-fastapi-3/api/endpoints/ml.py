# api/endpoints/ml.py
from fastapi import APIRouter, Depends, BackgroundTasks, status, HTTPException
import asyncpg
from uuid import UUID

from core.security import get_current_farmer
from schemas.farmer import FarmerResponse
from db.postgresql import db_pool 
from ml.tasks import run_training_cycle, run_prediction_cycle, train_model_for_cow
from db.postgresql import get_db_connection

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"],
    # Amankan semua endpoint di file ini
    dependencies=[Depends(get_current_farmer)] 
)

async def get_db_pool(conn: asyncpg.Connection = Depends(get_db_connection)) -> asyncpg.Pool:
    # Karena get_db_connection mengembalikan koneksi dari pool,
    # kita tahu pool-nya ada. Kita kembalikan referensi ke pool global.
    from db.postgresql import db_pool as global_db_pool
    if global_db_pool is None:
        raise HTTPException(status_code=503, detail="Database pool tidak tersedia.")
    return global_db_pool

@router.post("/trigger-training/all", status_code=status.HTTP_202_ACCEPTED)
async def trigger_full_training(
    background_tasks: BackgroundTasks,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Memicu siklus training ML (on-demand) untuk SEMUA sapi di background.
    """ 
    background_tasks.add_task(run_training_cycle, pool)
    return {"message": "Siklus training penuh telah dimulai di background."}

@router.post("/trigger-training/{cow_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cow_training(
    cow_id: UUID,
    background_tasks: BackgroundTasks,
    pool: asyncpg.Pool = Depends(get_db_pool)
    # TODO: Tambahkan dependency untuk memvalidasi kepemilikan sapi ini
):
    """
    Memicu siklus training ML (on-demand) untuk SATU sapi spesifik.
    """
    background_tasks.add_task(train_model_for_cow, pool, cow_id)
    return {"message": f"Siklus training untuk sapi {cow_id} telah dimulai."}
            
@router.post("/trigger-prediction", status_code=status.HTTP_202_ACCEPTED)
async def trigger_prediction(
    background_tasks: BackgroundTasks,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Memicu siklus prediksi anomali (on-demand) di background.
    """
        
    background_tasks.add_task(run_prediction_cycle, pool)
    return {"message": "Siklus prediksi anomali telah dimulai di background."}