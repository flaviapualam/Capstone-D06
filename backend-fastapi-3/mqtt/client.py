# mqtt/client.py
import asyncio
import json
import asyncpg
import aiomqtt
from datetime import datetime
from typing import List, Tuple, Dict, Any

from core.config import settings
from services.crud_sensor import batch_insert_sensor_data 
from services.crud_device import upsert_device_status
from services.crud_rfid import upsert_rfid_tags # <-- Impor baru

MQTT_DATA_BUFFER: List[Dict[str, Any]] = []
BUFFER_SIZE = 100 
BUFFER_TIMEOUT = 5.0 

async def flush_buffer_to_db(pool: asyncpg.Pool):
    global MQTT_DATA_BUFFER
    if not MQTT_DATA_BUFFER:
        return

    current_batch_dicts = MQTT_DATA_BUFFER
    MQTT_DATA_BUFFER = []
    
    device_updates: Dict[str, Tuple(str, datetime)] = {}
    output_sensor_batch: List[Tuple] = []
    rfid_ids_to_register: set = set() # <-- Set baru untuk menampung rfid

    for msg in current_batch_dicts:
        # 1. Siapkan data untuk output_sensor
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
        
        # 2. Siapkan data untuk update device
        device_updates[msg['device_id']] = (msg['ip'], msg['timestamp'])

        # 3. Siapkan data untuk registrasi RFID
        rfid = msg.get('rfid_id')
        if rfid: # Pastikan rfid tidak None
            rfid_ids_to_register.add(rfid)

    # Konversi set/dict ke list of tuples untuk 'executemany'
    device_upsert_batch = [
        (device_id, data[0], data[1]) 
        for device_id, data in device_updates.items()
    ]
    rfid_upsert_batch = [(rfid,) for rfid in rfid_ids_to_register] # <-- List baru
    
    try:
        async with pool.acquire() as connection:
            # --- URUTAN EKSEKUSI SANGAT PENTING ---

            # 1. Daftarkan/Update Device (Memenuhi FK pertama)
            if device_upsert_batch:
                await upsert_device_status(connection, device_upsert_batch)

            # 2. Daftarkan RFID (Memenuhi FK kedua)
            if rfid_upsert_batch:
                await upsert_rfid_tags(connection, rfid_upsert_batch)

            # 3. Masukkan Data Sensor (Semua FK sekarang valid)
            if output_sensor_batch:
                await batch_insert_sensor_data(connection, output_sensor_batch)
                
    except Exception as e:
        print(f"Failed to flush MQTT buffer to DB: {e}")
        MQTT_DATA_BUFFER.extend(current_batch_dicts)

async def process_mqtt_message(message: aiomqtt.Message):
    global MQTT_DATA_BUFFER
    
    try:
        payload = json.loads(message.payload.decode())
        device_id = payload.get("device_id")

        if not device_id:
            print(f"Error: 'device_id' tidak ditemukan di payload MQTT: {payload}")
            return

        record_dict = {
            "timestamp": datetime.now(),
            "device_id": device_id,
            "rfid_id": payload.get("rfid_id"),
            "weight": payload.get("weight"),
            "temperature_c": payload.get("temperature_c"),
            "ip": payload.get("ip")
        }
        
        MQTT_DATA_BUFFER.append(record_dict)
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        print(f"Topic: {str(message.topic)}, Payload: {message.payload.decode()}")

async def mqtt_listener_task(pool: asyncpg.Pool):
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
                    await process_mqtt_message(message)
                    
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