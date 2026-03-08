"""
Pydantic request/response schemas for the WebSocket gateway API.
"""

from typing import Optional, Dict, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class BroadcastRequest(BaseModel):
    """POST /broadcast — broadcast a message to connected clients."""
    channel: str = Field(..., description="Channel name to broadcast to")
    event: str = Field(..., description="Event type (e.g., 'ride_update', 'notification')")
    data: Dict = Field(default_factory=dict, description="Message payload")
    user_ids: Optional[List[str]] = Field(None, description="Target specific users (None = all)")


# ── Response schemas ──

class BroadcastResponse(BaseModel):
    """Response after broadcasting a message."""
    channel: str
    event: str
    recipients: int
    message: str = "Broadcast sent"


class WsInfoResponse(BaseModel):
    """GET /ws/info — WebSocket gateway stats."""
    active_connections: int
    max_connections: int
    uptime_seconds: int
    channels: List[str]
