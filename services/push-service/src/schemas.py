"""
Pydantic request/response schemas for the push notification service API.
"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


# ── Request schemas ──

class PushSendRequest(BaseModel):
    """POST /push/send — send a push notification to a single device."""
    device_token: str = Field(..., description="Device push token")
    title: str = Field(..., max_length=255)
    body: str = Field(..., description="Push notification body")
    data: Optional[Dict[str, str]] = Field(None, description="Custom data payload")


class PushSendBulkRequest(BaseModel):
    """POST /push/send-bulk — send push notifications to multiple devices."""
    device_tokens: List[str] = Field(..., min_length=1)
    title: str = Field(..., max_length=255)
    body: str = Field(..., description="Push notification body")
    data: Optional[Dict[str, str]] = Field(None, description="Custom data payload")


# ── Response schemas ──

class PushSendResponse(BaseModel):
    """Response after sending a push notification."""
    message_id: str
    status: str = "sent"
    provider: str = "firebase"


class PushBulkResponse(BaseModel):
    """Response after sending bulk push notifications."""
    total: int
    sent: int
    failed: int
    message_ids: List[str]


class PushStatusResponse(BaseModel):
    """GET /push/status/{id} — delivery status of a push notification."""
    message_id: str
    status: str
    delivered_at: Optional[str] = None
