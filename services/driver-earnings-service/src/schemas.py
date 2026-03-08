"""
Pydantic request/response schemas for the driver earnings service API.
"""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class EarningResponse(BaseModel):
    """Individual earning record."""
    id: str
    driver_id: str
    trip_id: Optional[str] = None
    amount: float
    currency: str
    earning_type: str
    description: Optional[str] = None
    earning_date: date
    created_at: datetime


class EarningListResponse(BaseModel):
    """GET /drivers/{id}/earnings response."""
    earnings: list[EarningResponse]
    total: int


class DailyEarningResponse(BaseModel):
    """Daily earnings aggregate."""
    date: date
    total_amount: float
    trip_count: int
    currency: str


class DailyEarningsListResponse(BaseModel):
    """GET /drivers/{id}/earnings/daily response."""
    daily_earnings: list[DailyEarningResponse]
    total_days: int


class EarningSummaryResponse(BaseModel):
    """GET /drivers/{id}/earnings/summary response."""
    driver_id: str
    total_earnings: float
    total_trips: int
    average_per_trip: float
    currency: str
