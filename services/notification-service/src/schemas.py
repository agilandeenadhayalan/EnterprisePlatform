"""
Pydantic request/response schemas for the notification service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class CreateNotificationRequest(BaseModel):
    """POST /notifications — create a new notification."""
    user_id: str = Field(..., description="Target user ID")
    title: str = Field(..., max_length=255)
    message: str = Field(..., description="Notification message body")
    notification_type: str = Field("info", description="Type: info, warning, alert, promo")
    channel: str = Field("in_app", description="Channel: in_app, push, email")


class MarkAllReadRequest(BaseModel):
    """POST /notifications/mark-all-read"""
    user_id: str


# ── Response schemas ──

class NotificationResponse(BaseModel):
    """Single notification response."""
    id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    channel: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """List of notifications with count."""
    notifications: List[NotificationResponse]
    count: int


class UnreadCountResponse(BaseModel):
    """Unread notification count for a user."""
    user_id: str
    unread_count: int


class MarkReadResponse(BaseModel):
    """Response after marking notification(s) as read."""
    message: str = "Marked as read"
    count: int = 1
