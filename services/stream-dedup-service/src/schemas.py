"""
Pydantic request/response schemas for the stream-dedup-service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class DedupBatchRequest(BaseModel):
    """POST /dedup — batch of events to deduplicate."""

    events: list[dict] = Field(..., description="List of event dicts with event_id field")
    event_id_field: str = Field("event_id", description="Field name for the unique event ID")


# -- Response schemas --


class DedupBatchResponse(BaseModel):
    """POST /dedup response."""

    unique_events: list[dict]
    duplicate_event_ids: list[str]
    unique_count: int
    duplicate_count: int
    total_checked: int


class DedupStatsResponse(BaseModel):
    """GET /dedup/stats response."""

    total_checked: int
    total_unique: int
    total_duplicates: int
    hit_rate: float
    miss_rate: float
    cache_size: int
    window_seconds: int
    max_cache_size: int
    uptime_seconds: float


class ClearCacheResponse(BaseModel):
    """DELETE /dedup/cache response."""

    cleared: int
    status: str
