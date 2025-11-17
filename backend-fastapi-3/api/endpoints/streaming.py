# api/endpoints/streaming.py
import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from core.security import get_current_farmer
from schemas.farmer import FarmerResponse
# Kita hanya perlu query sederhana, jadi kita tidak pakai crud_cow
from db.postgresql import get_db_connection
from streaming.broker import streaming_broker # Impor broker kita
import asyncpg

router = APIRouter(
    prefix="/streaming",
    tags=["Streaming (SSE)"],
    dependencies=[Depends(get_current_farmer)] # Amankan semua rute
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