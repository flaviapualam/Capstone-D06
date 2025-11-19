# services/crud_ml.py
import asyncpg
import json 
from uuid import UUID
from datetime import datetime, timedelta

async def get_sessions_for_training(
    db: asyncpg.Connection, 
    cow_id: UUID, 
    start_date: datetime, 
    end_date: datetime
) -> list[asyncpg.Record]:
    """
    Mengambil semua sesi makan untuk satu sapi dalam rentang waktu, 
    TERMASUK average_temp.
    """
    query = """
    SELECT *, average_temp FROM eat_session
    WHERE cow_id = $1 AND time_start BETWEEN $2 AND $3
    ORDER BY time_start;
    """
    return await db.fetch(query, cow_id, start_date, end_date)

# --- FUNGSI get_recent_sessions_before SUDAH DIHILANGKAN ---

async def save_new_model(
    db: asyncpg.Connection,
    cow_id: UUID | None,
    model_version: str,
    model_data: bytes,
    metrics: dict,
    start_date: datetime,
    end_date: datetime
):
    """
    Menyimpan model baru dan menonaktifkan model lama dalam satu transaksi.
    """
    try:
        async with db.transaction():
            if cow_id:
                await db.execute(
                    "UPDATE machine_learning_model SET is_active = false WHERE cow_id = $1 AND is_active = true",
                    cow_id
                )
            else:
                await db.execute(
                    "UPDATE machine_learning_model SET is_active = false WHERE cow_id IS NULL AND is_active = true"
                )
            
            await db.execute(
                """
                INSERT INTO machine_learning_model (
                    cow_id, model_version, model_data, 
                    training_data_start, training_data_end, metrics, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6, true);
                """,
                cow_id, model_version, model_data, start_date, end_date, json.dumps(metrics)
            )
        print(f"(ML Training) Model baru {model_version} untuk Sapi {cow_id} berhasil disimpan dan diaktifkan.")
    except Exception as e:
        print(f"Error saving new model: {e}")

async def get_active_model_for_cow(db: asyncpg.Connection, cow_id: UUID) -> asyncpg.Record | None:
    """
    Mengambil model per-sapi yang aktif. 
    Jika tidak ada, ambil model 'UMUM' yang aktif.
    """
    query = "SELECT * FROM machine_learning_model WHERE cow_id = $1 AND is_active = true"
    model = await db.fetchrow(query, cow_id)
    
    if model:
        return model
        
    query = "SELECT * FROM machine_learning_model WHERE cow_id IS NULL AND is_active = true"
    model = await db.fetchrow(query)
    return model

async def get_unscored_sessions(db: asyncpg.Connection) -> list[asyncpg.Record]:
    """
    Mengambil semua sesi makan yang belum ada di tabel 'anomaly'.
    """
    query = """
    SELECT es.* FROM eat_session es
    LEFT JOIN anomaly a ON es.session_id = a.session_id
    WHERE a.session_id IS NULL
    ORDER BY es.time_start
    LIMIT 1000; 
    """
    return await db.fetch(query)

async def save_anomaly_scores(db: asyncpg.Connection, anomaly_data: list[tuple]):
    """
    Menyimpan hasil deteksi anomali (batch insert).
    """
    query = """
    INSERT INTO anomaly (model_id, session_id, anomaly_score, is_anomaly)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (model_id, session_id) DO NOTHING;
    """
    try:
        await db.executemany(query, anomaly_data)
        print(f"(ML Prediction) Berhasil menyimpan {len(anomaly_data)} skor anomali.")
    except Exception as e:
        print(f"Error saving anomaly scores: {e}")