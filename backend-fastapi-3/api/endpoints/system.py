# api/endpoints/system.py
import asyncio
import json
from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from core.security import get_current_farmer
from schemas.farmer import FarmerResponse
from streaming.system_broker import system_broker # Import broker baru

router = APIRouter(
    prefix="/system",
    tags=["System Status"],
    dependencies=[Depends(get_current_farmer)] # Amankan rute
)

ML_TRAINING_CHANNEL = "ml_training_status"

async def _system_stream_generator(request: Request, queue: asyncio.Queue, channel_key: str):
    """Generator untuk SSE."""
    try:
        # Kirim pesan pembuka
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

@router.get("/stream/ml-status")
async def stream_ml_status(
    request: Request,
    current_farmer: FarmerResponse = Depends(get_current_farmer)
):
    """
    Endpoint SSE untuk streaming status training ML secara global.
    """
    # Hubungkan ke channel ML Training Status
    queue = await system_broker.connect(ML_TRAINING_CHANNEL)
    
    # Kembalikan StreamingResponse
    return StreamingResponse(
        _system_stream_generator(request, queue, ML_TRAINING_CHANNEL), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )