"""
Data models for stream-processor-metrics.

MetricEvent: raw metric event from Kafka.
WindowedAggregate: aggregated output from a tumbling window.
WindowState: current state of an active window.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MetricEvent(BaseModel):
    """Raw metric event consumed from Kafka."""

    event_id: str = Field(..., description="Unique event identifier")
    metric_name: str = Field(..., description="Metric name (e.g., 'ride_fare', 'ride_distance')")
    metric_value: float = Field(..., description="Metric value")
    dimensions: dict = Field(default_factory=dict, description="Dimension key-value pairs")
    timestamp: str = Field(..., description="Event timestamp ISO string")
    source: str = Field("unknown", description="Source service name")


class WindowedAggregate(BaseModel):
    """Aggregated metrics output from a tumbling window."""

    window_key: str
    metric_name: str
    window_start: datetime
    window_end: datetime
    count: int
    sum_value: float
    avg_value: float
    min_value: float
    max_value: float
    dimensions: dict
    flushed_at: datetime


class WindowState(BaseModel):
    """Current state of an active tumbling window."""

    window_key: str
    metric_name: str
    window_start: str
    window_end: str
    event_count: int
    current_sum: float
    current_min: float
    current_max: float
    is_open: bool = True
