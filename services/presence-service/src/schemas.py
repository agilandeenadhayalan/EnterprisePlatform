"""
Pydantic request/response schemas for the presence service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class HeartbeatRequest(BaseModel):
    """POST /users/{id}/heartbeat — user sends a heartbeat to stay online."""
    status: str = Field("online", description="Status: online, away, busy")


# ── Response schemas ──

class HeartbeatResponse(BaseModel):
    """Response after recording a heartbeat."""
    user_id: str
    status: str
    ttl_seconds: int
    message: str = "Heartbeat recorded"


class PresenceResponse(BaseModel):
    """GET /users/{id}/presence — current presence status."""
    user_id: str
    is_online: bool
    status: Optional[str] = None
    last_seen: Optional[str] = None


class OnlineCountResponse(BaseModel):
    """GET /presence/online-count — number of online users."""
    online_count: int
