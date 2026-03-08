"""
Pydantic request/response schemas for the activity service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -- Response schemas --

class ActivityResponse(BaseModel):
    """Activity log entry returned from the API."""
    id: int
    user_id: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime


class ActivityListResponse(BaseModel):
    """Paginated list of activity log entries."""
    items: list[ActivityResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False


# -- Request schemas --

class LogActivityRequest(BaseModel):
    """POST /activities — log a new activity (internal use)."""
    user_id: str = Field(..., description="UUID of the user performing the action")
    action: str = Field(..., min_length=1, max_length=100, description="e.g. login, ride_request, payment")
    resource_type: Optional[str] = Field(None, max_length=100, description="e.g. ride, payment, session")
    resource_id: Optional[str] = Field(None, max_length=255, description="ID of the affected resource")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent string")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional context as JSONB")
