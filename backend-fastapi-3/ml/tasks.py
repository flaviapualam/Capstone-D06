# ml/tasks.py
import asyncio
import asyncpg
import joblib
import numpy as np
import pandas as pd # <-- Impor pandas
import io
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from ml.isolation_forest import IsolationForest 
from services import crud_ml

# --- 1. LOGIKA FEATURE ENGINEERING (DIPERBARUI) ---

def engineer_features(sessions: List[Dict[str, Any]], window_size: int = 10) -> np.ndarray:
    """
    Mengubah list data sesi mentah menjadi array NumPy fitur.
    Termasuk fitur moving average (MA).
    """
    if not sessions:
        return np.empty((0, 8)) # 8 fitur

    # Buat DataFrame pandas dari list dictionary
    df = pd.DataFrame(sessions)

    # Fitur 1 & 2: Durasi & Konsumsi
    df['duration_sec'] = (df['time_end'] - df['time_start']).apply(lambda x: x.total_seconds())
    df['duration_min'] = df['duration_sec'] / 60.0
    df['total_consumption'] = df['weight_start'] - df['weight_end']
    
    # Fitur 3: Laju Konsumsi (kg/menit)
    # (Handling pembagian dengan nol)
    df['rate_per_min'] = 0.0
    mask = df['duration_sec'] > 0
    df.loc[mask, 'rate_per_min'] = (df['total_consumption'][mask] / df['duration_sec'][mask]) * 60

    # Fitur 4 & 5: Waktu Siklus (Cyclical Time) - 'hour_of_day'
    # Ini jauh lebih baik daripada 'hour' saja
    df['hour_sin'] = np.sin(2 * np.pi * df['time_start'].dt.hour / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['time_start'].dt.hour / 24.0)
    
    # Fitur 6: Hari dalam Seminggu
    df['day_of_week'] = df['time_start'].dt.weekday

    # --- FITUR MOVING AVERAGE (BARU) ---
    # Gunakan shift(1) agar rata-rata dihitung dari data SEBELUM sesi ini
    ma_consumption = df['total_consumption'].shift(1).rolling(window=window_size, min_periods=1).mean()
    ma_duration = df['duration_min'].shift(1).rolling(window=window_size, min_periods=1).mean()

    # Fitur 7: Deviasi Konsumsi (%) dari MA
    df['consumption_deviation'] = (df['total_consumption'] - ma_consumption) / ma_consumption
    
    # Fitur 8: Deviasi Durasi (%) dari MA
    df['duration_deviation'] = (df['duration_min'] - ma_duration) / ma_duration

    # --- Pembersihan Data ---
    # Ganti 'inf' (dari pembagian nol) & 'NaN' (dari rolling window pertama)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True) # Isi semua NaN (termasuk deviasi pertama) dengan 0

    # Pilih fitur final
    feature_columns = [
        'duration_min', 
        'total_consumption', 
        'rate_per_min',
        'hour_sin', 
        'hour_cos', 
        'day_of_week',
        'consumption_deviation',
        'duration_deviation'
    ]
    
    return df[feature_columns].values

# --- 2. TASK PELATIHAN (TRAINING TASK) (Diperbarui) ---

async def train_model_for_cow(pool: asyncpg.Pool, cow_id: UUID):
    """
    Logika lengkap untuk melatih satu model untuk satu sapi.
    """
    print(f"(ML Training) Memulai training untuk Sapi: {cow_id}")
    db: asyncpg.Connection
    async with pool.acquire() as db:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        session_records = await crud_ml.get_sessions_for_training(db, cow_id, start_date, end_date)
        
        if len(session_records) < 100: 
            print(f"(ML Training) Gagal: Data tidak cukup untuk Sapi {cow_id} (hanya {len(session_records)} sesi).")
            return

        sessions = [dict(record) for record in session_records]
        
        # Panggil feature engineering baru
        X_train = engineer_features(sessions, window_size=10) 
        
        if X_train.size == 0:
             print(f"(ML Training) Gagal: Feature engineering menghasilkan data kosong untuk Sapi {cow_id}.")
             return

        model = IsolationForest(contamination=0.05)
        model.fit(X_train)
        
        model_buffer = io.BytesIO()
        joblib.dump(model, model_buffer)
        model_data = model_buffer.getvalue()
        
        model_version = f"iforest-v2-ma-{end_date.strftime('%Y%m%d')}"
        metrics = {
            "feature_count": X_train.shape[1], 
            "session_count": X_train.shape[0],
            "anomaly_threshold": model.threshold_
        }
        
        await crud_ml.save_new_model(
            db, cow_id, model_version, model_data, 
            metrics, start_date, end_date
        )

# (Fungsi 'periodic_training_task' tetap sama, ia hanya memanggil 'train_model_for_cow')
async def periodic_training_task(pool: asyncpg.Pool):
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        print(f"(ML Training) Task training tidur, akan berjalan dalam {wait_seconds/3600:.2f} jam.")
        await asyncio.sleep(wait_seconds)
        
        print(f"(ML Training) Memulai siklus training harian...")
        
        cows_to_train = []
        try:
            async with pool.acquire() as db:
                 cow_records = await db.fetch("SELECT cow_id FROM cow")
                 cows_to_train = [record['cow_id'] for record in cow_records]
        except Exception as e:
            print(f"Error mengambil daftar sapi: {e}")

        for cow_id in cows_to_train:
            try:
                await train_model_for_cow(pool, cow_id)
            except Exception as e:
                print(f"Error training model untuk Sapi {cow_id}: {e}")
        
        print("(ML Training) Siklus training harian selesai.")

# --- 3. TASK PREDIKSI (INFERENCE TASK) (Diperbarui) ---

async def periodic_prediction_task(pool: asyncpg.Pool):
    """
    (TASK B) Berjalan setiap 1 jam, menilai sesi makan yang baru.
    """
    while True:
        print(f"(ML Prediction) Memulai siklus prediksi...")
        
        loaded_models: Dict[UUID, IsolationForest] = {}
        
        db: asyncpg.Connection
        async with pool.acquire() as db:
            unscored_sessions = await crud_ml.get_unscored_sessions(db)
            if not unscored_sessions:
                print("(ML Prediction) Tidak ada sesi baru untuk dinilai.")
                await asyncio.sleep(3600)
                continue
                
            print(f"(ML Prediction) Menilai {len(unscored_sessions)} sesi baru...")
            
            results_to_save = []
            
            for session_record in unscored_sessions:
                session = dict(session_record)
                cow_id = session['cow_id']
                
                try:
                    # 1. Muat Model (dari cache atau DB)
                    if cow_id not in loaded_models:
                        model_record_raw = await crud_ml.get_active_model_for_cow(db, cow_id)
                        if not model_record_raw:
                            print(f"Warning: Tidak ada model aktif untuk Sapi {cow_id}. Sesi dilewati.")
                            continue
                        
                        model_record = dict(model_record_raw) # Konversi ke dict
                        model_buffer = io.BytesIO(model_record['model_data'])
                        loaded_models[cow_id] = {
                            "model": joblib.load(model_buffer),
                            "model_id": model_record['model_id']
                        }
                    
                    model_pack = loaded_models[cow_id]
                    model = model_pack["model"]
                    model_id = model_pack["model_id"]
                    
                    # --- 2. LOGIKA PREDIKSI BARU ---
                    # Ambil 9 sesi terakhir untuk membangun konteks MA
                    # (window_size - 1)
                    history_records = await crud_ml.get_recent_sessions_before(
                        db, cow_id, session['time_start'], limit=9 
                    )
                    
                    # Gabungkan riwayat + sesi saat ini
                    all_sessions_for_calc = [dict(r) for r in history_records] + [session]
                    
                    # 3. Feature Engineering
                    # 'engineer_features' akan menghitung MA untuk semua 10,
                    # tapi kita hanya tertarik pada baris terakhir.
                    features_array = engineer_features(all_sessions_for_calc, window_size=10)
                    
                    if features_array.size == 0:
                        continue
                        
                    # Ambil fitur untuk sesi saat ini (baris terakhir)
                    current_features = features_array[-1:] 
                    
                    # 4. Lakukan Prediksi
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

        print("(ML Prediction) Siklus prediksi selesai.")
        await asyncio.sleep(3600) # Tidur 1 jam