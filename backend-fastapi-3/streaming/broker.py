# streaming/broker.py
import asyncio
import json
from uuid import UUID
from typing import Dict, List, Any

class StreamingBroker:
    """
    Broker Pub/Sub sederhana di dalam memori untuk menyiarkan
    pesan ke klien SSE yang terhubung.
    """
    def __init__(self):
        # Menyimpan daftar antrian (queues) untuk setiap cow_id
        self.clients: Dict[UUID, List[asyncio.Queue]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, cow_id: UUID) -> asyncio.Queue:
        """
        Klien baru (dari SSE) terhubung dan mendaftar untuk
        menerima update untuk cow_id tertentu.
        """
        async with self.lock:
            queue = asyncio.Queue()
            # setdefault adalah cara aman untuk membuat list jika belum ada
            self.clients.setdefault(cow_id, []).append(queue)
            print(f"(Stream) Klien terhubung untuk Sapi {cow_id}. Total: {len(self.clients[cow_id])}")
            return queue

    async def disconnect(self, cow_id: UUID, queue: asyncio.Queue):
        """Klien (dari SSE) terputus."""
        async with self.lock:
            if cow_id in self.clients:
                try:
                    self.clients[cow_id].remove(queue)
                    if not self.clients[cow_id]: # Hapus jika list kosong
                        del self.clients[cow_id]
                    print(f"(Stream) Klien terputus untuk Sapi {cow_id}.")
                except ValueError:
                    pass # Antrian sudah dihapus

    async def broadcast(self, cow_id: UUID, message: Dict[str, Any]):
        """
        Dipanggil oleh MQTT. Menyebarkan pesan ke semua klien
        yang mendengarkan cow_id ini.
        """
        if cow_id in self.clients:
            # Ubah ke string JSON sekali saja
            message_str = json.dumps(message) 
            
            # Kita lakukan iterasi tanpa lock untuk kecepatan.
            # 'put' pada asyncio.Queue aman untuk thread/task.
            for queue in self.clients[cow_id]:
                await queue.put(message_str)

# Buat satu instance global yang akan digunakan di seluruh aplikasi
streaming_broker = StreamingBroker()