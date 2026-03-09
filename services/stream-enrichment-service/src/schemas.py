"""
Pydantic request/response schemas for the stream-enrichment-service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class EnrichBatchRequest(BaseModel):
    """POST /enrich — batch of events to enrich."""

    events: list[dict] = Field(..., description="List of raw event dicts to enrich")


# -- Response schemas --


class EnrichedEventResponse(BaseModel):
    """Single enriched event."""

    event_id: str
    event_type: str
    pickup_zone_name: Optional[str] = None
    pickup_borough: Optional[str] = None
    dropoff_zone_name: Optional[str] = None
    dropoff_borough: Optional[str] = None
    weather_condition: Optional[str] = None
    temperature_f: Optional[float] = None
    precipitation: Optional[bool] = None
    enriched_at: str
    payload: dict


class EnrichBatchResponse(BaseModel):
    """POST /enrich response."""

    enriched: int
    failed: int
    results: list[EnrichedEventResponse]


class DimensionCacheResponse(BaseModel):
    """GET /dimensions response."""

    zone_count: int
    weather_count: int
    last_refreshed_at: Optional[str] = None
    zones: dict
    weather: dict


class RefreshResponse(BaseModel):
    """POST /dimensions/refresh response."""

    zones_loaded: int
    weather_loaded: int
    status: str
