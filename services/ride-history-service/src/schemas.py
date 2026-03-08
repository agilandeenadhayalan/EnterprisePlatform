"""Pydantic schemas for ride history service."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class HistoryTripResponse(BaseModel):
    id: str
    rider_id: str
    driver_id: Optional[str] = None
    status: str
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    actual_distance_km: Optional[float] = None
    actual_duration_minutes: Optional[int] = None
    fare_amount: Optional[float] = None
    currency: str = "USD"
    vehicle_type: Optional[str] = None
    requested_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HistoryListResponse(BaseModel):
    trips: List[HistoryTripResponse]
    count: int


class RiderStatsResponse(BaseModel):
    rider_id: str
    total_trips: int
    completed_trips: int
    cancelled_trips: int
    total_spent: float
    average_fare: Optional[float] = None
