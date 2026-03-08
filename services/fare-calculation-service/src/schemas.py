"""Pydantic schemas for the fare calculation service API."""

from typing import Optional

from pydantic import BaseModel, Field


class FareCalculateRequest(BaseModel):
    """POST /fare/calculate — detailed fare calculation."""
    base_fare: float = Field(..., ge=0)
    distance_miles: float = Field(..., ge=0)
    per_mile_rate: float = Field(..., ge=0)
    duration_minutes: float = Field(..., ge=0)
    per_minute_rate: float = Field(..., ge=0)
    booking_fee: float = Field(2.50, ge=0)
    minimum_fare: float = Field(5.00, ge=0)


class FareBreakdownRequest(BaseModel):
    """POST /fare/breakdown — breakdown from raw inputs."""
    base_fare: float = Field(..., ge=0)
    distance_miles: float = Field(..., ge=0)
    per_mile_rate: float = Field(..., ge=0)
    duration_minutes: float = Field(..., ge=0)
    per_minute_rate: float = Field(..., ge=0)
    booking_fee: float = Field(2.50, ge=0)
    discount_amount: float = Field(0.0, ge=0)
    minimum_fare: float = Field(5.00, ge=0)


class FareWithSurgeRequest(BaseModel):
    """POST /fare/with-surge — fare calculation with surge."""
    base_fare: float = Field(..., ge=0)
    distance_miles: float = Field(..., ge=0)
    per_mile_rate: float = Field(..., ge=0)
    duration_minutes: float = Field(..., ge=0)
    per_minute_rate: float = Field(..., ge=0)
    booking_fee: float = Field(2.50, ge=0)
    surge_multiplier: float = Field(1.0, ge=1.0)
    discount_amount: float = Field(0.0, ge=0)
    minimum_fare: float = Field(5.00, ge=0)


class FareBreakdownResponse(BaseModel):
    """Detailed fare breakdown."""
    base_fare: float
    distance_charge: float
    time_charge: float
    booking_fee: float
    surge_multiplier: float
    surge_charge: float
    discount_amount: float
    subtotal: float
    total: float
    minimum_fare_applied: bool
