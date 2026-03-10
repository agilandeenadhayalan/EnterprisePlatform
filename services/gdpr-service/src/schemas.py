"""
Pydantic request/response schemas for the GDPR API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class DSRCreate(BaseModel):
    """POST /gdpr/requests — submit a data subject request."""
    request_type: str = Field(..., description="Request type: access, erasure, portability, rectification")
    subject_email: str = Field(..., description="Data subject email address")
    data_categories: Optional[list[str]] = Field(default=None, description="Categories of data requested")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class DSRUpdate(BaseModel):
    """PATCH /gdpr/requests/{id} — update request status."""
    status: Optional[str] = None
    notes: Optional[str] = None


class ConsentCreate(BaseModel):
    """POST /gdpr/consent — record consent grant/withdrawal."""
    subject_email: str = Field(..., description="Data subject email address")
    purpose: str = Field(..., description="Consent purpose (e.g. marketing, analytics)")
    granted: bool = Field(default=True, description="Whether consent is granted or withdrawn")


# ── Response schemas ──

class DSRResponse(BaseModel):
    """A data subject request."""
    id: str
    request_type: str
    subject_email: str
    status: str
    data_categories: list[str] = []
    submitted_at: datetime
    due_date: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class ConsentResponse(BaseModel):
    """A consent record."""
    id: str
    subject_email: str
    purpose: str
    granted: bool
    timestamp: datetime


class AuditEntry(BaseModel):
    """An audit trail entry."""
    action: str
    timestamp: datetime
    details: Optional[str] = None
