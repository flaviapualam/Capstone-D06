# api/endpoints/ml.py
from fastapi import APIRouter, Depends, BackgroundTasks, status, HTTPException
import asyncpg
from uuid import UUID

from core.security import get_current_farmer
from schemas.farmer import FarmerResponse
# Impor db_pool langsung untuk BackgroundTasks
from db.postgresql import db_pool 
# Impor fungsi siklus yang dapat dipanggil
from ml.tasks import run_training_cycle, run_prediction_cycle, train_model_for_cow

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"],
    # Amankan semua endpoint di file ini
    dependencies=[Depends(get_current_farmer)] 
)

@router.post("/trigger-training/all", status_code=status.HTTP_202_ACCEPTED)
async def trigger_full_training(
    background_tasks: BackgroundTasks
):
    """
    Memicu siklus training ML (on-demand) untuk SEMUA sapi di background.
    """
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database pool tidak tersedia")
        
    background_tasks.add_task(run_training_cycle, db_pool)
    return {"message": "Siklus training penuh telah dimulai di background."}

@router.post("/trigger-training/{cow_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cow_training(
    cow_id: UUID,
    background_tasks: BackgroundTasks
    # TODO: Tambahkan dependency untuk memvalidasi kepemilikan sapi ini
):
    """
    Memicu siklus training ML (on-demand) untuk SATU sapi spesifik.
    """
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database pool tidak tersedia")

    background_tasks.add_task(train_model_for_cow, db_pool, cow_id)
    return {"message": f"Siklus training untuk sapi {cow_id} telah dimulai."}
            
@router.post("/trigger-prediction", status_code=status.HTTP_202_ACCEPTED)
async def trigger_prediction(
    background_tasks: BackgroundTasks
):
    """
    Memicu siklus prediksi anomali (on-demand) di background.
    """
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database pool tidak tersedia")
        
    background_tasks.add_task(run_prediction_cycle, db_pool)
    return {"message": "Siklus prediksi anomali telah dimulai di background."}