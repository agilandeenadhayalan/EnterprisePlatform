"""
Pydantic request/response schemas for the stream-processor-locations API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class ProcessBatchRequest(BaseModel):
    """POST /process — batch of location events to process."""

    events: list[dict] = Field(..., description="List of raw location event dicts")


# -- Response schemas --


class ProcessedLocationResponse(BaseModel):
    """Single processed location result."""

    driver_id: str
    latitude: float
    longitude: float
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    speed_kmh: float
    status: str
    processed_at: str


class ProcessBatchResponse(BaseModel):
    """POST /process response."""

    buffered: int
    flushed: int
    failed: int
    results: list[ProcessedLocationResponse]


class BufferStatsResponse(BaseModel):
    """GET /process/stats response."""

    buffer_size: int
    total_received: int
    total_flushed: int
    total_errors: int
    flush_count: int
    last_flush_at: Optional[str] = None
    last_received_at: Optional[str] = None
    uptime_seconds: float


class FlushResponse(BaseModel):
    """POST /process/flush response."""

    flushed: int
    status: str
