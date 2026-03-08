"""Pydantic schemas for the payment service API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    trip_id: str
    rider_id: str
    driver_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    payment_method_id: Optional[str] = None


class UpdatePaymentStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|processing|completed|failed|refunded)$")
    payment_gateway_ref: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str
    trip_id: str
    rider_id: str
    driver_id: Optional[str] = None
    amount: float
    currency: str
    payment_method_id: Optional[str] = None
    status: str
    payment_gateway_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime
