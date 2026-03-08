"""
Pydantic request/response schemas for the session service API.

These define the API contract — what clients send and receive.
Session data never exposes the refresh_token in responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    """Single session details — returned in list and detail endpoints."""
    id: str
    user_id: str
    device_info: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime
    expires_at: datetime


class SessionListResponse(BaseModel):
    """GET /sessions — list of active sessions for the current user."""
    sessions: list[SessionResponse]
    count: int


class SessionCountResponse(BaseModel):
    """GET /sessions/active/count — number of active sessions."""
    active_count: int
