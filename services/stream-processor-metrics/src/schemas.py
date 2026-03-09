"""
Pydantic request/response schemas for the stream-processor-metrics API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --


class ProcessBatchRequest(BaseModel):
    """POST /process — batch of metric events to process."""

    events: list[dict] = Field(..., description="List of raw metric event dicts")


# -- Response schemas --


class ProcessBatchResponse(BaseModel):
    """POST /process response."""

    accepted: int
    failed: int
    windows_updated: int


class WindowStateResponse(BaseModel):
    """Single window state."""

    window_key: str
    metric_name: str
    window_start: str
    window_end: str
    event_count: int
    current_sum: float
    current_min: float
    current_max: float
    is_open: bool


class ActiveWindowsResponse(BaseModel):
    """GET /windows response."""

    active_windows: list[WindowStateResponse]
    total: int


class WindowedAggregateResponse(BaseModel):
    """Single flushed aggregate."""

    window_key: str
    metric_name: str
    window_start: str
    window_end: str
    count: int
    sum_value: float
    avg_value: float
    min_value: float
    max_value: float


class FlushResponse(BaseModel):
    """POST /windows/flush response."""

    flushed: int
    aggregates: list[WindowedAggregateResponse]


class ProcessingStatsResponse(BaseModel):
    """GET /process/stats response."""

    events_processed: int
    events_failed: int
    windows_created: int
    windows_flushed: int
    active_window_count: int
    last_processed_at: Optional[str] = None
    uptime_seconds: float
