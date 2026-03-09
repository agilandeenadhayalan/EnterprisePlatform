"""
Pydantic request/response schemas for the stream-processor-rides API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class ProcessBatchRequest(BaseModel):
    """POST /process — batch of ride events to process."""

    events: list[dict] = Field(..., description="List of raw ride event dicts")


class ReplayRequest(BaseModel):
    """POST /process/replay — replay events from a time range."""

    start_time: str = Field(..., description="Start of replay range (ISO 8601)")
    end_time: str = Field(..., description="End of replay range (ISO 8601)")
    topic: str = Field("ride.events.v1", description="Kafka topic to replay from")


# -- Response schemas --


class ProcessedRideResponse(BaseModel):
    """Single processed ride result."""

    ride_id: str
    driver_id: str
    rider_id: str
    fare_amount: float
    total_amount: float
    trip_duration_minutes: float
    speed_mph: float
    pickup_hour: int
    pickup_day_of_week: int
    is_weekend: bool
    processed_at: str


class ProcessBatchResponse(BaseModel):
    """POST /process response."""

    processed: int
    failed: int
    results: list[ProcessedRideResponse]


class ProcessingStatsResponse(BaseModel):
    """GET /process/stats response."""

    events_processed: int
    events_failed: int
    error_count: int
    last_processed_at: Optional[str] = None
    avg_processing_time_ms: float
    uptime_seconds: float


class ReplayResponse(BaseModel):
    """POST /process/replay response."""

    status: str
    replayed_count: int
    start_time: str
    end_time: str
