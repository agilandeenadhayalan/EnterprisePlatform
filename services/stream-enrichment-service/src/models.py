"""
Data models for stream-enrichment-service.

RawEvent: raw event to be enriched.
EnrichedEvent: event after dimension lookups.
DimensionCache: cached dimension data.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RawEvent(BaseModel):
    """Raw event to be enriched with dimension data."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of event (ride, location, payment)")
    pickup_zone_id: Optional[int] = Field(None, description="Pickup zone ID for lookup")
    dropoff_zone_id: Optional[int] = Field(None, description="Dropoff zone ID for lookup")
    timestamp: str = Field(..., description="Event timestamp ISO string")
    payload: dict = Field(default_factory=dict, description="Event payload data")


class EnrichedEvent(BaseModel):
    """Event enriched with dimension data from cache."""

    event_id: str
    event_type: str
    pickup_zone_id: Optional[int] = None
    pickup_zone_name: Optional[str] = None
    pickup_borough: Optional[str] = None
    dropoff_zone_id: Optional[int] = None
    dropoff_zone_name: Optional[str] = None
    dropoff_borough: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_f: Optional[float] = None
    precipitation: Optional[bool] = None
    timestamp: str
    payload: dict
    enriched_at: str


class DimensionCache(BaseModel):
    """Cached dimension data for enrichment."""

    zones: dict = Field(default_factory=dict, description="Zone ID -> zone info mapping")
    weather: dict = Field(default_factory=dict, description="Date-hour -> weather info mapping")
    last_refreshed_at: Optional[str] = None
    zone_count: int = 0
    weather_count: int = 0
