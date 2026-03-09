"""
Data models for stream-processor-rides.

RideEvent: raw event from Kafka topic.
RideFact: transformed record for ClickHouse fact_rides table.
ProcessingStats: runtime statistics for the processor.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RideEvent(BaseModel):
    """Raw ride event consumed from Kafka."""

    event_id: str = Field(..., description="Unique event identifier")
    ride_id: str = Field(..., description="Ride identifier")
    driver_id: str = Field(..., description="Driver identifier")
    rider_id: str = Field(..., description="Rider identifier")
    pickup_latitude: float = Field(..., description="Pickup latitude")
    pickup_longitude: float = Field(..., description="Pickup longitude")
    dropoff_latitude: float = Field(..., description="Dropoff latitude")
    dropoff_longitude: float = Field(..., description="Dropoff longitude")
    pickup_zone_id: Optional[int] = Field(None, description="Pickup zone ID")
    dropoff_zone_id: Optional[int] = Field(None, description="Dropoff zone ID")
    ride_status: str = Field("completed", description="Ride status")
    fare_amount: float = Field(0.0, description="Fare amount in USD")
    tip_amount: float = Field(0.0, description="Tip amount in USD")
    distance_miles: float = Field(0.0, description="Trip distance in miles")
    pickup_at: str = Field(..., description="Pickup datetime ISO string")
    dropoff_at: str = Field(..., description="Dropoff datetime ISO string")
    vehicle_type: str = Field("sedan", description="Vehicle type")
    payment_method: str = Field("card", description="Payment method")
    surge_multiplier: float = Field(1.0, description="Surge pricing multiplier")


class RideFact(BaseModel):
    """Transformed ride record for ClickHouse fact_rides table."""

    ride_id: str
    driver_id: str
    rider_id: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    pickup_zone_id: Optional[int] = None
    dropoff_zone_id: Optional[int] = None
    ride_status: str
    fare_amount: float
    tip_amount: float
    total_amount: float
    distance_miles: float
    trip_duration_minutes: float
    speed_mph: float
    pickup_at: datetime
    dropoff_at: datetime
    pickup_hour: int
    pickup_day_of_week: int
    is_weekend: bool
    vehicle_type: str
    payment_method: str
    surge_multiplier: float
    processed_at: datetime


class ProcessingStats(BaseModel):
    """Processing statistics for the stream processor."""

    events_processed: int = 0
    events_failed: int = 0
    error_count: int = 0
    last_processed_at: Optional[str] = None
    avg_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0
