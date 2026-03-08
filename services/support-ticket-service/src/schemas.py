"""
Pydantic request/response schemas for the support ticket service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class CreateTicketRequest(BaseModel):
    """POST /tickets — create a new support ticket."""
    user_id: str = Field(..., description="User creating the ticket")
    subject: str = Field(..., max_length=255)
    description: str = Field(..., description="Detailed description of the issue")
    category: str = Field("general", description="Category: general, billing, ride, driver, technical")
    priority: str = Field("medium", description="Priority: low, medium, high, urgent")


class UpdateTicketStatusRequest(BaseModel):
    """PATCH /tickets/{id}/status — update ticket status."""
    status: str = Field(..., description="New status: open, in_progress, resolved, closed")
    assigned_to: Optional[str] = Field(None, description="Agent ID to assign ticket to")


# ── Response schemas ──

class TicketResponse(BaseModel):
    """Single support ticket response."""
    id: str
    user_id: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    """List of support tickets."""
    tickets: List[TicketResponse]
    count: int
