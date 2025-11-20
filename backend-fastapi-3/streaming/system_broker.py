# streaming/system_broker.py
import asyncio
import json
from typing import Dict, List, Any

class SystemBroker:
    """
    Broker Pub/Sub untuk event sistem global (misalnya, status ML training).
    Kunci channel-nya adalah string (misal: 'global_alerts').
    """
    def __init__(self):
        # Kunci channel adalah string (misalnya 'global_alerts', 'ml_status')
        self.clients: Dict[str, List[asyncio.Queue]] = {} 
        self.lock = asyncio.Lock()

    async def connect(self, channel_key: str) -> asyncio.Queue:
        """Klien terhubung ke channel sistem yang spesifik."""
        async with self.lock:
            queue = asyncio.Queue()
            self.clients.setdefault(channel_key, []).append(queue)
            print(f"(SysStream) Client connected to channel: {channel_key}")
            return queue

    async def disconnect(self, channel_key: str, queue: asyncio.Queue):
        """Klien terputus."""
        async with self.lock:
            if channel_key in self.clients:
                try:
                    self.clients[channel_key].remove(queue)
                    if not self.clients[channel_key]:
                        del self.clients[channel_key]
                    print(f"(SysStream) Client disconnected from channel: {channel_key}")
                except ValueError:
                    pass

    async def broadcast(self, channel_key: str, message: Dict[str, Any]):
        """Menyiarkan pesan sistem ke semua klien yang terhubung ke channel_key."""
        if channel_key in self.clients:
            message_str = json.dumps(message) 
            for queue in self.clients[channel_key]:
                await queue.put(message_str)

# Buat instance global
system_broker = SystemBroker()