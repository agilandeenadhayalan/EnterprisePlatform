"""Pydantic schemas for the refund service API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CreateRefundRequest(BaseModel):
    payment_id: str
    rider_id: str
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None

class ApproveRefundRequest(BaseModel):
    approved_by: str

class RefundResponse(BaseModel):
    id: str
    payment_id: str
    rider_id: str
    amount: float
    reason: Optional[str] = None
    status: str
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class RefundListResponse(BaseModel):
    refunds: list[RefundResponse]
    count: int
