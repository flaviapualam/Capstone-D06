# api/endpoints/ml.py
from fastapi import APIRouter, Depends, BackgroundTasks, status, HTTPException, Query
import asyncpg
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta

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

@router.get("/anomaly")
async def get_anomalies(
    cow_id: Optional[UUID] = Query(None, description="Filter by specific cow ID"),
    days: int = Query(7, description="Number of days to look back"),
    current_farmer: FarmerResponse = Depends(get_current_farmer),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Get anomaly detection results for the farmer's cows.
    Optionally filter by specific cow_id.
    """
    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Base query to get anomalies from actual schema
        if cow_id:
            # Verify cow ownership
            verify_query = """
                SELECT cow_id FROM cow 
                WHERE cow_id = $1 AND farmer_id = $2
            """
            cow_check = await conn.fetchrow(verify_query, cow_id, current_farmer.farmer_id)
            if not cow_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cow not found or not owned by current farmer"
                )
            
            # Get anomalies for specific cow
            query = """
                SELECT 
                    a.session_id,
                    a.anomaly_score,
                    a.is_anomaly,
                    e.cow_id,
                    c.name as cow_name,
                    e.time_end as timestamp,
                    e.average_temp
                FROM anomaly a
                JOIN eat_session e ON a.session_id = e.session_id
                JOIN cow c ON e.cow_id = c.cow_id
                WHERE e.cow_id = $1 
                    AND e.time_end >= $2 
                    AND e.time_end <= $3
                    AND a.is_anomaly = true
                ORDER BY e.time_end DESC
            """
            rows = await conn.fetch(query, cow_id, start_time, end_time)
        else:
            # Get anomalies for all farmer's cows
            query = """
                SELECT 
                    a.session_id,
                    a.anomaly_score,
                    a.is_anomaly,
                    e.cow_id,
                    c.name as cow_name,
                    e.time_end as timestamp,
                    e.average_temp
                FROM anomaly a
                JOIN eat_session e ON a.session_id = e.session_id
                JOIN cow c ON e.cow_id = c.cow_id
                WHERE c.farmer_id = $1 
                    AND e.time_end >= $2 
                    AND e.time_end <= $3
                    AND a.is_anomaly = true
                ORDER BY e.time_end DESC
            """
            rows = await conn.fetch(query, current_farmer.farmer_id, start_time, end_time)
        
        # Format anomalies
        anomalies = []
        for row in rows:
            anomalies.append({
                "anomaly_id": str(row['session_id']),  # Use session_id as anomaly_id
                "session_id": str(row['session_id']),
                "cow_id": str(row['cow_id']),
                "cow_name": row['cow_name'],
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "anomaly_score": float(row['anomaly_score']) if row['anomaly_score'] else 0.0,
                "is_anomaly": row['is_anomaly'],
                "avg_temperature": float(row['average_temp']) if row['average_temp'] else None
            })
        
        return {"anomalies": anomalies}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomalies: {str(e)}"
        )

@router.post("/anomaly/{session_id}/resend-email", status_code=status.HTTP_200_OK)
async def resend_anomaly_email(
    session_id: UUID,
    current_farmer: FarmerResponse = Depends(get_current_farmer),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Resend email notification for a specific anomaly session.
    """
    try:
        # Verify anomaly session exists and belongs to farmer's cow
        query = """
            SELECT 
                a.session_id,
                a.anomaly_score,
                e.cow_id,
                c.name as cow_name,
                e.time_end as timestamp,
                e.average_temp,
                f.email,
                f.name as farmer_name
            FROM anomaly a
            JOIN eat_session e ON a.session_id = e.session_id
            JOIN cow c ON e.cow_id = c.cow_id
            JOIN farmer f ON c.farmer_id = f.farmer_id
            WHERE a.session_id = $1 AND f.farmer_id = $2 AND a.is_anomaly = true
        """
        anomaly = await conn.fetchrow(query, session_id, current_farmer.farmer_id)
        
        if not anomaly:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Anomaly session not found or not owned by current farmer"
            )
        
        # Send email using email service
        from services.email import send_anomaly_alert
        await send_anomaly_alert(
            farmer_email=anomaly['email'],
            cow_id=anomaly['cow_id'],
            score=float(anomaly['anomaly_score']) if anomaly['anomaly_score'] else 0.0,
            avg_temp=float(anomaly['average_temp']) if anomaly['average_temp'] else 0.0,
            time=anomaly['timestamp']
        )
        
        return {"message": "Email notification sent successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend email: {str(e)}"
        )