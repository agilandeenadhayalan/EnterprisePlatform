"""
Presence service repository — in-memory presence store (simulates Redis).

In production, this would use Redis SET with TTL for each user's heartbeat.
For now, it uses an in-memory dict with timestamp-based expiry checks.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional


class PresenceRepository:
    """In-memory presence store (simulates Redis with TTL)."""

    def __init__(self, ttl_seconds: int = 60):
        self._store: Dict[str, Dict] = {}
        self._ttl = ttl_seconds

    async def record_heartbeat(self, user_id: str, status: str = "online") -> None:
        """Record a heartbeat for a user."""
        self._store[user_id] = {
            "status": status,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self._ttl),
        }

    async def get_presence(self, user_id: str) -> Optional[Dict]:
        """Get presence status for a user."""
        data = self._store.get(user_id)
        if not data:
            return None
        # Check if heartbeat has expired
        if datetime.now(timezone.utc) > data["expires_at"]:
            return {"is_online": False, "status": None, "last_seen": data["last_seen"]}
        return {"is_online": True, "status": data["status"], "last_seen": data["last_seen"]}

    async def get_online_count(self) -> int:
        """Count currently online users."""
        now = datetime.now(timezone.utc)
        return sum(1 for d in self._store.values() if now <= d["expires_at"])
