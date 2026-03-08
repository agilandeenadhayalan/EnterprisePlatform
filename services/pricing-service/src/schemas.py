"""
Pydantic request/response schemas for the pricing service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class FareEstimateRequest(BaseModel):
    """POST /estimate — calculate fare estimate."""
    vehicle_type: str = Field(..., description="Vehicle type (e.g., economy, premium, xl)")
    distance_miles: float = Field(..., gt=0, description="Trip distance in miles")
    duration_minutes: float = Field(..., gt=0, description="Estimated trip duration in minutes")
    surge_multiplier: float = Field(1.0, ge=1.0, description="Surge pricing multiplier")


class FareCalculateRequest(BaseModel):
    """POST /calculate — finalize fare after trip completion."""
    vehicle_type: str
    distance_miles: float = Field(..., gt=0)
    duration_minutes: float = Field(..., gt=0)
    surge_multiplier: float = Field(1.0, ge=1.0)
    discount_amount: float = Field(0.0, ge=0)


# ── Response schemas ──

class FareEstimateResponse(BaseModel):
    """Fare estimate breakdown."""
    vehicle_type: str
    base_fare: float
    distance_charge: float
    time_charge: float
    booking_fee: float
    surge_multiplier: float
    surge_charge: float
    subtotal: float
    total: float
    minimum_fare: float


class FareCalculateResponse(BaseModel):
    """Finalized fare breakdown."""
    vehicle_type: str
    base_fare: float
    distance_charge: float
    time_charge: float
    booking_fee: float
    surge_multiplier: float
    surge_charge: float
    discount_amount: float
    subtotal: float
    total: float


class PricingRuleResponse(BaseModel):
    """Single pricing rule."""
    id: str
    vehicle_type: str
    base_fare: float
    per_mile_rate: float
    per_minute_rate: float
    booking_fee: float
    minimum_fare: float
    is_active: bool
    created_at: datetime


class PricingRuleListResponse(BaseModel):
    """GET /rules — all pricing rules."""
    rules: list[PricingRuleResponse]
    count: int
