"""Pydantic schemas for the discount service API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ValidateDiscountRequest(BaseModel):
    """POST /discounts/validate — check if a code is valid."""
    code: str = Field(..., min_length=1, max_length=50)
    fare_amount: Optional[float] = Field(None, ge=0)


class ApplyDiscountRequest(BaseModel):
    """POST /discounts/apply — apply discount to a fare."""
    code: str = Field(..., min_length=1, max_length=50)
    fare_amount: float = Field(..., gt=0)


class CreateDiscountRequest(BaseModel):
    """POST /discounts — create a new discount code."""
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    discount_value: float = Field(..., gt=0)
    max_uses: Optional[int] = Field(None, gt=0)
    min_fare_amount: Optional[float] = Field(None, ge=0)
    max_discount_amount: Optional[float] = Field(None, gt=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class DiscountResponse(BaseModel):
    id: str
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    max_uses: Optional[int] = None
    current_uses: int
    min_fare_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: datetime


class ValidateDiscountResponse(BaseModel):
    code: str
    is_valid: bool
    reason: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None


class ApplyDiscountResponse(BaseModel):
    code: str
    original_fare: float
    discount_amount: float
    final_fare: float


class DiscountListResponse(BaseModel):
    discounts: list[DiscountResponse]
    count: int
