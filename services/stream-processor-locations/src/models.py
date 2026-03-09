"""
Data models for stream-processor-locations.

LocationEvent: raw driver location event from Kafka.
LocationFact: transformed record for ClickHouse fact_driver_locations.
BufferStats: statistics about the location buffer.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LocationEvent(BaseModel):
    """Raw driver location event from Kafka."""

    event_id: str = Field(..., description="Unique event identifier")
    driver_id: str = Field(..., description="Driver identifier")
    latitude: float = Field(..., description="Current latitude")
    longitude: float = Field(..., description="Current longitude")
    heading: float = Field(0.0, description="Heading in degrees (0-360)")
    speed_kmh: float = Field(0.0, description="Speed in km/h")
    accuracy_meters: float = Field(10.0, description="GPS accuracy in meters")
    timestamp: str = Field(..., description="Event timestamp ISO string")
    status: str = Field("online", description="Driver status (online/busy/offline)")
    ride_id: Optional[str] = Field(None, description="Active ride ID if any")


class LocationFact(BaseModel):
    """Transformed location record for ClickHouse fact_driver_locations."""

    driver_id: str
    latitude: float
    longitude: float
    heading: float
    speed_kmh: float
    accuracy_meters: float
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    status: str
    ride_id: Optional[str] = None
    timestamp: datetime
    processed_at: datetime


class BufferStats(BaseModel):
    """Statistics about the location buffer and processing."""

    buffer_size: int = 0
    total_received: int = 0
    total_flushed: int = 0
    total_errors: int = 0
    flush_count: int = 0
    last_flush_at: Optional[str] = None
    last_received_at: Optional[str] = None
    uptime_seconds: float = 0.0
