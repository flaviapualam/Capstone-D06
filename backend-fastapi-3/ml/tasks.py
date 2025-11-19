# ml/tasks.py
import asyncio
import asyncpg
import joblib
import numpy as np
import pandas as pd
import io
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from ml.isolation_forest import IsolationForest 
from services import crud_ml


def engineer_features(sessions: List[Dict[str, Any]]) -> np.ndarray: # <-- window_size dihapus
    """
    Mengubah list data sesi mentah menjadi array NumPy fitur.
    (Hanya fitur dasar dan siklus waktu).
    """
    if not sessions:
        return np.empty((0, 7))

    df = pd.DataFrame(sessions)

    df['duration_sec'] = (df['time_end'] - df['time_start']).apply(lambda x: x.total_seconds())
    df['duration_min'] = df['duration_sec'] / 60.0
    df['total_consumption'] = df['weight_start'] - df['weight_end']
    
    df['rate_per_min'] = 0.0
    mask = df['duration_sec'] > 0
    df.loc[mask, 'rate_per_min'] = (df['total_consumption'][mask] / df['duration_sec'][mask]) * 60

    df['hour_sin'] = np.sin(2 * np.pi * df['time_start'].dt.hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['time_start'].dt.hour / 24.0)
    df['day_of_week'] = df['time_start'].dt.weekday

    df['avg_temp'] = df['average_temp']

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)

    feature_columns = [
        'duration_min', 'total_consumption', 'rate_per_min',
        'hour_sin', 'hour_cos', 'day_of_week',
        'avg_temp'
    ]
    
    return df[feature_columns].values

async def train_model_for_cow(pool: asyncpg.Pool, cow_id: UUID):
    print(f"(ML Training) Memulai training untuk Sapi: {cow_id}")
    db: asyncpg.Connection
    async with pool.acquire() as db:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        session_records = await crud_ml.get_sessions_for_training(db, cow_id, start_date, end_date)
        
        if len(session_records) < 10:
            print(f"(ML Training) Gagal: Data tidak cukup untuk Sapi {cow_id} (hanya {len(session_records)} sesi).")
            return

        sessions = [dict(record) for record in session_records]
        X_train = engineer_features(sessions)
        
        if X_train.size == 0:
             print(f"(ML Training) Gagal: Feature engineering menghasilkan data kosong untuk Sapi {cow_id}.")
             return

        model = IsolationForest(contamination=0.05)
        model.fit(X_train)
        
        model_buffer = io.BytesIO()
        joblib.dump(model, model_buffer)
        model_data = model_buffer.getvalue()
        
        model_version = f"iforest-v3-base-{end_date.strftime('%Y%m%d')}"
        metrics = {
            "feature_count": X_train.shape[1], 
            "session_count": X_train.shape[0],
            "anomaly_threshold": model.threshold_
        }
        
        await crud_ml.save_new_model(
            db, cow_id, model_version, model_data, 
            metrics, start_date, end_date
        )

async def run_training_cycle(pool: asyncpg.Pool):
    """
    Menjalankan satu siklus training penuh untuk semua sapi.
    """
    print(f"(ML Training) [Cycle Start] Memulai siklus training...")
    
    cows_to_train = []
    try:
        async with pool.acquire() as db:
             cow_records = await db.fetch("SELECT cow_id FROM cow")
             cows_to_train = [record['cow_id'] for record in cow_records]
    except Exception as e:
        print(f"Error mengambil daftar sapi: {e}")
        return

    for cow_id in cows_to_train:
        try:
            await train_model_for_cow(pool, cow_id)
        except Exception as e:
            print(f"Error training model untuk Sapi {cow_id}: {e}")
    
    print("(ML Training) [Cycle End] Siklus training selesai.")


async def run_prediction_cycle(pool: asyncpg.Pool):
    """
    Menjalankan satu siklus prediksi penuh untuk sesi yang belum dinilai.
    (Logika disederhanakan karena tidak perlu mengambil riwayat).
    """
    print(f"(ML Prediction) [Cycle Start] Memulai siklus prediksi...")
    
    loaded_models: Dict[UUID, IsolationForest] = {}
    
    db: asyncpg.Connection
    async with pool.acquire() as db:
        unscored_sessions = await crud_ml.get_unscored_sessions(db)
        if not unscored_sessions:
            print("(ML Prediction) Tidak ada sesi baru untuk dinilai.")
            return
            
        print(f"(ML Prediction) Menilai {len(unscored_sessions)} sesi baru...")
        
        results_to_save = []
        
        for session_record in unscored_sessions:
            session = dict(session_record)
            cow_id = session['cow_id']
            
            try:
                if cow_id not in loaded_models:
                    model_record_raw = await crud_ml.get_active_model_for_cow(db, cow_id)
                    if not model_record_raw:
                        print(f"Warning: Tidak ada model aktif untuk Sapi {cow_id}. Sesi dilewati.")
                        continue
                    
                    model_record = dict(model_record_raw)
                    model_buffer = io.BytesIO(model_record['model_data'])
                    loaded_models[cow_id] = {
                        "model": joblib.load(model_buffer),
                        "model_id": model_record['model_id']
                    }
                
                model_pack = loaded_models[cow_id]
                model = model_pack["model"]
                model_id = model_pack["model_id"]
                
                features_array = engineer_features([session]) 
                
                if features_array.size == 0:
                    continue
                        
                current_features = features_array[0].reshape(1, -1) # Ambil fitur pertama dan reshape
                
                score = model.score_samples(current_features)[0]
                prediction = model.predict(current_features)[0]
                
                results_to_save.append(
                    (
                        model_id,
                        session['session_id'],
                        float(score),
                        True if prediction == -1 else False
                    )
                )
            except Exception as e:
                print(f"Error menilai sesi {session.get('session_id')}: {e}")

        if results_to_save:
            await crud_ml.save_anomaly_scores(db, results_to_save)

    print("(ML Prediction) [Cycle End] Siklus prediksi selesai.")

async def periodic_training_task(pool: asyncpg.Pool):
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        print(f"(ML Training) Task training tidur, akan berjalan dalam {wait_seconds/3600:.2f} jam.")
        await asyncio.sleep(wait_seconds)
        
        await run_training_cycle(pool)

async def periodic_prediction_task(pool: asyncpg.Pool):
    while True:
        await run_prediction_cycle(pool)
        
        print(f"(ML Prediction) [Periodic] Siklus selesai. Tidur selama 1 jam.")
        await asyncio.sleep(3600)