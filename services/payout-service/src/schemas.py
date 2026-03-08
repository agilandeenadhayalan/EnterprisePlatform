"""Pydantic schemas for the payout service API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CreatePayoutRequest(BaseModel):
    driver_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    payout_method: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

class PayoutResponse(BaseModel):
    id: str
    driver_id: str
    amount: float
    currency: str
    status: str
    payout_method: Optional[str] = None
    reference: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime

class PayoutListResponse(BaseModel):
    payouts: list[PayoutResponse]
    count: int
