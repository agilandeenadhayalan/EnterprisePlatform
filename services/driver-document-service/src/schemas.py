"""
Pydantic request/response schemas for the driver document service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    """POST /documents — upload a document."""
    driver_id: str
    document_type: str = Field(..., max_length=50, description="e.g., license, insurance, registration")
    document_number: Optional[str] = Field(None, max_length=100)
    file_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class DocumentVerifyRequest(BaseModel):
    """PATCH /documents/{id}/verify — verify or reject a document."""
    status: str = Field(..., pattern="^(verified|rejected)$")
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)


class DocumentResponse(BaseModel):
    """Document record."""
    id: str
    driver_id: str
    document_type: str
    document_number: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """GET /drivers/{id}/documents response."""
    documents: list[DocumentResponse]
    total: int
