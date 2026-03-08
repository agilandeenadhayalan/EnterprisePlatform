"""
Pydantic request/response schemas for the chat service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class CreateRoomRequest(BaseModel):
    """POST /rooms — create a new chat room."""
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    room_type: str = Field("trip", description="Room type: trip, support")
    participant_ids: List[str] = Field(..., min_length=1, description="List of participant user IDs")


class SendMessageRequest(BaseModel):
    """POST /rooms/{id}/messages — send a message to a room."""
    sender_id: str = Field(..., description="Sender user ID")
    message: str = Field(..., description="Message content")
    message_type: str = Field("text", description="Message type: text, image, location")


# ── Response schemas ──

class ChatRoomResponse(BaseModel):
    """Single chat room response."""
    id: str
    trip_id: Optional[str] = None
    room_type: str
    participant_ids: List[str]
    created_at: datetime


class ChatMessageResponse(BaseModel):
    """Single chat message response."""
    id: str
    room_id: str
    sender_id: str
    message: str
    message_type: str
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    """List of chat messages with count."""
    messages: List[ChatMessageResponse]
    count: int
