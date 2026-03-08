"""
Pydantic request/response schemas for the driver incentive service API.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class IncentiveCreateRequest(BaseModel):
    """POST /incentives — create a new incentive."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    incentive_type: str = Field("bonus", max_length=30)
    amount: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=3)
    criteria: Optional[dict[str, Any]] = None
    starts_at: datetime
    ends_at: datetime
    max_claims: Optional[int] = Field(None, gt=0)


class IncentiveResponse(BaseModel):
    """Incentive record."""
    id: str
    title: str
    description: Optional[str] = None
    incentive_type: str
    amount: float
    currency: str
    criteria: Optional[dict[str, Any]] = None
    is_active: bool
    starts_at: datetime
    ends_at: datetime
    max_claims: Optional[int] = None
    current_claims: int
    created_at: datetime
    updated_at: datetime


class IncentiveListResponse(BaseModel):
    """GET /incentives response."""
    incentives: list[IncentiveResponse]
    total: int
