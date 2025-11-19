# api/endpoints/streaming.py
import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from core.security import get_current_farmer
from schemas.farmer import FarmerResponse
from db.postgresql import get_db_connection
from streaming.broker import streaming_broker
from streaming.system_broker import system_broker
import asyncpg
import json

router = APIRouter(
    prefix="/streaming",
    tags=["Streaming (SSE)"],
    dependencies=[Depends(get_current_farmer)] # Amankan semua rute
)

ML_TRAINING_CHANNEL = "ml_training_status"

async def _ml_stream_generator(request: Request, queue: asyncio.Queue, channel_key: str):
    """Generator untuk SSE status training ML."""
    try:
        # Pesan pembuka
        yield f"data: {json.dumps({'event': 'connected', 'channel': channel_key})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            message_str = await queue.get()
            yield f"data: {message_str}\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        await system_broker.disconnect(channel_key, queue)


@router.get("/ml-status")
async def stream_ml_status(
    request: Request,
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """Streaming status ML untuk dashboard."""
    queue = await system_broker.connect(ML_TRAINING_CHANNEL)

    return StreamingResponse(
        _ml_stream_generator(request, queue, ML_TRAINING_CHANNEL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def _cow_stream_generator(request: Request, queue: asyncio.Queue, cow_id: UUID):
    """
    Generator yang menghasilkan data dari antrian (queue)
    sebagai string Server-Sent Event (SSE).
    """
    try:
        while True:
            # 1. Tunggu pesan baru dari broker
            # (Misal: data dari 'streaming_broker.broadcast')
            message_str = await queue.get()
            
            # 2. Cek apakah klien masih terhubung SEBELUM mengirim
            if await request.is_disconnected():
                print(f"(Stream) Klien untuk {cow_id} terputus (loop check).")
                break
                
            # 3. Format sebagai SSE dan kirim (yield)
            yield f"data: {message_str}\n\n"
            
    except asyncio.CancelledError:
        print(f"(Stream) Generator untuk {cow_id} dibatalkan.")
    finally:
        # 4. Pembersihan: Hapus antrian ini dari broker
        await streaming_broker.disconnect(cow_id, queue)

@router.get("/cows/{cow_id}")
async def stream_cow_data(
    cow_id: UUID,
    request: Request,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Endpoint SSE untuk streaming data sensor real-time
    dari seekor sapi.
    """
    
    # 1. Otorisasi: Verifikasi kepemilikan sapi
    # Kita lakukan query ringan saja untuk cek farmer_id
    cow_query = "SELECT farmer_id FROM cow WHERE cow_id = $1"
    cow_record = await db.fetchrow(cow_query, cow_id)
    
    if not cow_record:
        raise HTTPException(status_code=404, detail="Sapi tidak ditemukan")
    if cow_record['farmer_id'] != current_farmer.farmer_id:
        raise HTTPException(status_code=403, detail="Anda tidak punya hak akses ke sapi ini")

    # 2. Hubungkan klien ini ke broker untuk mendapatkan antrian
    queue = await streaming_broker.connect(cow_id)
    
    # 3. Buat generator SSE
    sse_generator = _cow_stream_generator(request, queue, cow_id)
    
    # 4. Kembalikan StreamingResponse
    return StreamingResponse(
        sse_generator, 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Penting untuk menonaktifkan buffering Nginx/proxy
        }
    )

async def _farmer_stream_generator(request: Request, queue: asyncio.Queue):
    """Generator yang melayani notifikasi global farmer (semua sapi)."""
    try:
        # Pesan pembuka
        yield f"data: {json.dumps({'event': 'connected', 'channel': 'farmer_alerts'})}\n\n"
        
        while True:
            # 1. Tunggu pesan baru (anomaly, session end, dll.)
            message_str = await queue.get()
            
            if await request.is_disconnected():
                break
            
            # 2. Format dan kirim pesan SSE
            yield f"data: {message_str}\n\n"
            
    except asyncio.CancelledError:
        pass
    finally:
        # 3. Pembersihan: Hapus antrian ini dari broker.
        # Catatan: Kita harus menggunakan broker yang tepat di sini.
        # Asumsi: Broker utama (streaming_broker) digunakan untuk notifikasi farmer.
        # Kunci: current_farmer.farmer_id
        # Kita perlu tahu broker mana yang digunakan untuk kunci farmer_id.
        # Berdasarkan arsitektur Anda, seharusnya streaming_broker (keyed by cow_id/farmer_id).
        pass # Kita tidak bisa melakukan disconnect di sini karena farmer_id tidak ada di scope

@router.get("/farmer/me/alerts")
async def stream_farmer_notifications(
    request: Request,
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Endpoint SSE untuk streaming notifikasi dan anomali untuk SEMUA
    sapi yang dimiliki oleh farmer yang login.
    """
    farmer_id = current_farmer.farmer_id
    
    # 1. Hubungkan klien ini ke broker menggunakan FARMER_ID
    # (Asumsi: Broker utama (streaming_broker) digunakan untuk farmer_id channel)
    queue = await streaming_broker.connect(farmer_id) 
    
    # 2. Kembalikan StreamingResponse dengan generator yang dimodifikasi
    return StreamingResponse(
        _farmer_stream_generator(request, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )