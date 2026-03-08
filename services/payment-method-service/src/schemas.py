"""Pydantic schemas for the payment method service API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CreatePaymentMethodRequest(BaseModel):
    user_id: str
    method_type: str = Field(..., pattern="^(card|bank_account|wallet)$")
    provider: Optional[str] = None
    last_four: Optional[str] = Field(None, min_length=4, max_length=4)
    expiry_month: Optional[str] = Field(None, min_length=2, max_length=2)
    expiry_year: Optional[str] = Field(None, min_length=4, max_length=4)
    is_default: bool = False
    token_ref: Optional[str] = None

class PaymentMethodResponse(BaseModel):
    id: str
    user_id: str
    method_type: str
    provider: Optional[str] = None
    last_four: Optional[str] = None
    expiry_month: Optional[str] = None
    expiry_year: Optional[str] = None
    is_default: bool
    is_active: bool
    created_at: datetime

class PaymentMethodListResponse(BaseModel):
    payment_methods: list[PaymentMethodResponse]
    count: int
