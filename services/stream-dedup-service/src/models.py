"""
Data models for stream-dedup-service.

DedupRequest: batch of events to deduplicate.
DedupResult: result of deduplication check.
DedupStats: deduplication statistics.
"""

from typing import Optional

from pydantic import BaseModel, Field


class DedupRequest(BaseModel):
    """Batch of events to check for duplicates."""

    events: list[dict] = Field(..., description="List of event dicts with 'event_id' field")
    event_id_field: str = Field("event_id", description="Field name for the event ID")


class DedupResult(BaseModel):
    """Result of deduplication — unique and duplicate events."""

    unique_events: list[dict] = Field(default_factory=list)
    duplicate_event_ids: list[str] = Field(default_factory=list)
    unique_count: int = 0
    duplicate_count: int = 0
    total_checked: int = 0


class DedupStats(BaseModel):
    """Deduplication cache and processing statistics."""

    total_checked: int = 0
    total_unique: int = 0
    total_duplicates: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    cache_size: int = 0
    window_seconds: int = 3600
    max_cache_size: int = 100000
    uptime_seconds: float = 0.0
