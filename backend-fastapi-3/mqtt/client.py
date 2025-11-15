# mqtt/client.py
import asyncio
import json
import asyncpg
import aiomqtt
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

from core.config import settings
from services.crud_sensor import batch_insert_sensor_data 
from services.crud_device import upsert_device_status
from services.crud_rfid import upsert_rfid_tags
# 1. Impor service baru kita
from services.crud_session import get_active_cow_by_rfid, create_eat_session

# --- Buffer untuk 'output_sensor' (tetap sama) ---
MQTT_DATA_BUFFER: List[Dict[str, Any]] = []
BUFFER_SIZE = 100 
BUFFER_TIMEOUT = 5.0 

# --- State Machine untuk 'eat_session' (BARU) ---
# Kamus untuk melacak sesi yang sedang aktif di setiap perangkat
# Key: device_id, Value: dict state sesi
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Timeout sesi sekarang 1 menit (60 detik)
SESSION_TIMEOUT_SECONDS = 60 

# --- FUNGSI BUFFER (Logika ini tetap sama) ---
async def flush_buffer_to_db(pool: asyncpg.Pool):
    global MQTT_DATA_BUFFER
    if not MQTT_DATA_BUFFER:
        return

    current_batch_dicts = MQTT_DATA_BUFFER
    MQTT_DATA_BUFFER = []
    
    device_updates: Dict[str, Tuple(str, datetime)] = {}
    output_sensor_batch: List[Tuple] = []
    rfid_ids_to_register: set = set()

    for msg in current_batch_dicts:
        output_sensor_batch.append(
            (
                msg['timestamp'],
                msg['device_id'],
                msg['rfid_id'],
                msg['weight'],
                msg['temperature_c'],
                msg['ip']
            )
        )
        device_updates[msg['device_id']] = (msg['ip'], msg['timestamp'])
        rfid = msg.get('rfid_id')
        if rfid:
            rfid_ids_to_register.add(rfid)

    device_upsert_batch = [(d, data[0], data[1]) for d, data in device_updates.items()]
    rfid_upsert_batch = [(rfid,) for rfid in rfid_ids_to_register]
    
    try:
        async with pool.acquire() as connection:
            if device_upsert_batch:
                await upsert_device_status(connection, device_upsert_batch)
            if rfid_upsert_batch:
                await upsert_rfid_tags(connection, rfid_upsert_batch)
            if output_sensor_batch:
                await batch_insert_sensor_data(connection, output_sensor_batch)
    except Exception as e:
        print(f"Failed to flush MQTT buffer to DB: {e}")
        MQTT_DATA_BUFFER.extend(current_batch_dicts)


# --- FUNGSI LOGIKA SESI (BARU) ---

async def finalize_session(pool: asyncpg.Pool, device_id: str, last_weight: float, last_timestamp: datetime):
    """Mengakhiri sesi dan menyimpannya ke DB."""
    state = ACTIVE_SESSIONS.pop(device_id, None)
    if not state:
        return

    async with pool.acquire() as db:
        await create_eat_session(
            db=db,
            device_id=device_id,
            rfid_id=state['rfid_id'],
            cow_id=state['cow_id'],
            time_start=state['time_start'],
            time_end=last_timestamp,
            weight_start=state['weight_start'],
            weight_end=last_weight
        )

async def start_new_session(
    pool: asyncpg.Pool, 
    device_id: str, 
    rfid_id: str, 
    weight: float, 
    timestamp: datetime
):
    """Memvalidasi RFID dan memulai sesi baru di memori."""
    cow_id = None
    async with pool.acquire() as db:
        cow_id = await get_active_cow_by_rfid(db, rfid_id)
    
    # Constraint: Hanya mulai jika RFID terdaftar dan dimiliki
    if not cow_id:
        print(f"Ignoring session start for unassigned RFID: {rfid_id}")
        return

    ACTIVE_SESSIONS[device_id] = {
        "rfid_id": rfid_id,
        "cow_id": cow_id,
        "time_start": timestamp,
        "weight_start": weight,
        "last_weight": weight,
        "last_seen": timestamp
    }
    print(f"(SESSION START) Cow {cow_id} detected at {device_id}.")

async def process_mqtt_message(pool: asyncpg.Pool, message: aiomqtt.Message):
    """
    Memproses SATU pesan MQTT:
    1. Menambahkannya ke buffer output_sensor.
    2. Menjalankan state machine untuk eat_session.
    """
    global MQTT_DATA_BUFFER
    
    try:
        payload = json.loads(message.payload.decode())
        device_id = payload.get("device_id")
        if not device_id:
            return

        # Ambil timestamp dari server, BUKAN dari payload
        timestamp = datetime.now()
        
        # 1. Tambahkan ke Buffer (untuk 'output_sensor' dan 'device')
        record_dict = {
            "timestamp": timestamp, # Gunakan timestamp server
            "device_id": device_id,
            "rfid_id": payload.get("rfid_id"),
            "weight": payload.get("weight"),
            "temperature_c": payload.get("temperature_c"),
            "ip": payload.get("ip")
        }
        MQTT_DATA_BUFFER.append(record_dict)

        # 2. Jalankan State Machine (untuk 'eat_session')
        new_rfid = payload.get("rfid_id")
        new_weight = payload.get("weight")
        
        state = ACTIVE_SESSIONS.get(device_id)
        current_rfid = state['rfid_id'] if state else None
        
        if new_rfid == current_rfid:
            # KASUS 1: Sesi berlanjut (atau feeder tetap kosong)
            if state:
                state['last_weight'] = new_weight
                state['last_seen'] = timestamp
        else:
            # KASUS 2: Terjadi perubahan!
            
            # Jika ada sesi LAMA, akhiri dulu
            if state:
                await finalize_session(pool, device_id, state['last_weight'], state['last_seen'])
            
            # Jika ada RFID BARU, mulai sesi baru
            if new_rfid and new_weight is not None:
                await start_new_session(pool, device_id, new_rfid, new_weight, timestamp)
                
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        print(f"Topic: {str(message.topic)}, Payload: {message.payload.decode()}")

# --- FUNGSI TASK (Logika diubah) ---

async def check_session_timeouts(pool: asyncpg.Pool):
    """Fungsi pembantu yang menjalankan logika timeout."""
    now = datetime.now()
    timeout_threshold = timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    
    # Buat salinan keys() untuk menghindari error 'dictionary changed size'
    for device_id in list(ACTIVE_SESSIONS.keys()):
        state = ACTIVE_SESSIONS.get(device_id)
        if not state: 
            continue
            
        if now - state['last_seen'] > timeout_threshold:
            print(f"Session for {device_id} timed out (1 min). Finalizing...")
            await finalize_session(
                pool, 
                device_id, 
                state['last_weight'], 
                state['last_seen']
            )

async def session_timeout_checker_task(pool: asyncpg.Pool):
    """
    (TASK 1) Berjalan di background, mengecek sesi timeout setiap 10 detik.
    """
    while True:
        await asyncio.sleep(10) # Cek setiap 10 detik
        try:
            await check_session_timeouts(pool)
        except Exception as e:
            print(f"Error in session timeout checker task: {e}")

async def mqtt_listener_task(pool: asyncpg.Pool):
    """
    (TASK 2) Berjalan di background, mendengarkan MQTT dan mem-flush buffer.
    """
    subscription_topic = f"{settings.MQTT_TOPIC_PREFIX}"
    print(f"Connecting to MQTT Broker at {settings.MQTT_BROKER_HOST}...")
    
    last_flush_time = asyncio.get_event_loop().time()

    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_HOST, 
                port=settings.MQTT_BROKER_PORT
            ) as client:
                print(f"MQTT Client connected. Subscribing to '{subscription_topic}'")
                await client.subscribe(subscription_topic)
                
                async for message in client.messages:
                    # Teruskan 'pool' ke process_mqtt_message
                    await process_mqtt_message(pool, message)
                    
                    current_time = asyncio.get_event_loop().time()
                    if (len(MQTT_DATA_BUFFER) >= BUFFER_SIZE or 
                        current_time - last_flush_time >= BUFFER_TIMEOUT):
                        
                        await flush_buffer_to_db(pool)
                        last_flush_time = current_time
                    
        except aiomqtt.MqttError as e:
            print(f"MQTT connection error, reconnecting in 5 seconds... Error: {e}")
            await flush_buffer_to_db(pool)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred in MQTT task, restarting... Error: {e}")
            await asyncio.sleep(5)