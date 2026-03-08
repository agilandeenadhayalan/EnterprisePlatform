"""
WebSocket gateway repository — in-memory connection manager.

In production, this would manage actual WebSocket connections and
coordinate across instances via Redis pub/sub. For now, it provides
a stub broadcast mechanism.
"""

import time
from typing import Dict, List, Optional


class WsConnectionManager:
    """Stubbed WebSocket connection manager."""

    def __init__(self):
        self._connections: Dict[str, List[str]] = {}  # channel -> [user_ids]
        self._start_time = time.time()

    async def broadcast(
        self,
        channel: str,
        event: str,
        data: Dict,
        user_ids: Optional[List[str]] = None,
    ) -> int:
        """Broadcast a message to a channel. Returns recipient count."""
        # In production: iterate WebSocket connections and send
        subscribers = self._connections.get(channel, [])
        if user_ids:
            recipients = [uid for uid in subscribers if uid in user_ids]
        else:
            recipients = subscribers
        return len(recipients)

    async def get_info(self) -> Dict:
        """Get gateway stats."""
        total_connections = sum(len(users) for users in self._connections.values())
        return {
            "active_connections": total_connections,
            "channels": list(self._connections.keys()),
            "uptime_seconds": int(time.time() - self._start_time),
        }
