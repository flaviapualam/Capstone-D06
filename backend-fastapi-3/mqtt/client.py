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
from services.crud_session import get_active_cow_by_rfid, create_eat_session

from streaming.broker import streaming_broker

MQTT_DATA_BUFFER: List[Dict[str, Any]] = []
BUFFER_SIZE = 100 
BUFFER_TIMEOUT = 5.0 

ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TIMEOUT_SECONDS = 60 

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

    device_upsert_batch = [
        (device_id, data[0], data[1]) 
        for device_id, data in device_updates.items()
    ]
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

async def finalize_session(pool: asyncpg.Pool, device_id: str, last_weight: float, last_timestamp: datetime):
    state = ACTIVE_SESSIONS.pop(device_id, None)
    if not state:
        return
    end_message = {
        "cow_id": str(state['cow_id']),
        "event": "session_end",
        "device_id": device_id,
        "timestamp": last_timestamp.isoformat()
    }
    await streaming_broker.broadcast(state['cow_id'], end_message)

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
    cow_id = None
    async with pool.acquire() as db:
        cow_id = await get_active_cow_by_rfid(db, rfid_id)
    
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
    global MQTT_DATA_BUFFER
    
    try:
        payload = json.loads(message.payload.decode())
        
        device_id = payload.get("id")
        if not device_id:
            print(f"Error: 'id' (device_id) tidak ditemukan di payload MQTT: {payload}")
            return

        client_timestamp_str = payload.get("ts")
        timestamp_obj: datetime
        
        if not client_timestamp_str:
            print(f"Warning: 'ts' (timestamp) tidak ada di payload. Gunakan waktu server.")
            timestamp_obj = datetime.now()
        else:
            try:
                timestamp_obj = datetime.fromisoformat(client_timestamp_str)
            except (ValueError, TypeError):
                print(f"Error: Format 'ts' tidak valid: '{client_timestamp_str}'. Gunakan waktu server.")
                timestamp_obj = datetime.now()
        new_rfid = payload.get("rfid")
        new_weight = payload.get("w")
        new_temp = payload.get("temp")
        new_ip = payload.get("ip")
        
        record_dict = {
            "timestamp": timestamp_obj,
            "device_id": device_id,
            "rfid_id": new_rfid,
            "weight": new_weight,
            "temperature_c": new_temp,
            "ip": new_ip
        }
        MQTT_DATA_BUFFER.append(record_dict)

        state = ACTIVE_SESSIONS.get(device_id)
        current_rfid = state['rfid_id'] if state else None
        
        if new_rfid == current_rfid:
            if state:
                state['last_weight'] = new_weight
                state['last_seen'] = timestamp_obj

                broadcast_message = {
                    "cow_id": str(state['cow_id']),
                    "timestamp": timestamp_obj.isoformat(),
                    "weight": new_weight,
                    "temperature_c": new_temp,
                    "device_id": device_id,
                    "event": "sensor_update"
                }
                await streaming_broker.broadcast(state['cow_id'], broadcast_message)
        else:
            if state:
                await finalize_session(pool, device_id, state['last_weight'], state['last_seen'])
            
            if new_rfid and new_weight is not None:
                await start_new_session(pool, device_id, new_rfid, new_weight, timestamp_obj)
                
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        print(f"Topic: {str(message.topic)}, Payload: {message.payload.decode()}")

async def check_session_timeouts(pool: asyncpg.Pool):
    now = datetime.now()
    timeout_threshold = timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    
    for device_id in list(ACTIVE_SESSIONS.keys()):
        state = ACTIVE_SESSIONS.get(device_id)
        if not state: 
            continue
            
        if now - state['last_seen'] > timeout_threshold:
            print(f"Session for {device_id} timed out (1 min). Finalizing...")

            timeout_msg = {
                "cow_id": str(state['cow_id']), 
                "event": "session_timeout",
                "device_id": device_id,
                "timestamp": state['last_seen'].isoformat()
            }
            await streaming_broker.broadcast(state['cow_id'], timeout_msg)
            
            await finalize_session(
                pool, 
                device_id, 
                state['last_weight'], 
                state['last_seen']
            )

async def session_timeout_checker_task(pool: asyncpg.Pool):
    while True:
        await asyncio.sleep(10)
        try:
            await check_session_timeouts(pool)
        except Exception as e:
            print(f"Error in session timeout checker task: {e}")

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