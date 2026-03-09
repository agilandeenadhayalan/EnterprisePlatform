"""
Pydantic request/response schemas for the dashboard API.
"""

from typing import Any

from pydantic import BaseModel


# ── Response schemas ──


class DashboardOverviewResponse(BaseModel):
    """Platform overview metrics."""
    total_rides: int
    total_revenue: float
    active_drivers: int
    avg_fare: float
    rides_growth_pct: float
    revenue_growth_pct: float
    drivers_growth_pct: float


class RealtimeMetricsResponse(BaseModel):
    """Real-time platform metrics."""
    rides_in_progress: int
    active_drivers: int
    queued_requests: int
    avg_wait_time_seconds: float
    recent_events: list[dict[str, Any]]


class ZoneHeatmapEntryResponse(BaseModel):
    """Zone heatmap data entry."""
    zone_id: int
    zone_name: str
    ride_count: int
    revenue: float
    avg_fare: float
    lat: float
    lng: float


class ZoneHeatmapResponse(BaseModel):
    """List of zone heatmap entries."""
    zones: list[ZoneHeatmapEntryResponse]
    total: int


class TrendDataPointResponse(BaseModel):
    """A single trend data point."""
    period: str
    ride_count: int
    revenue: float


class TrendDataResponse(BaseModel):
    """Time series trend data."""
    data_points: list[TrendDataPointResponse]
    total: int


class SystemAlertResponse(BaseModel):
    """System alert entry."""
    id: str
    severity: str
    category: str
    message: str
    created_at: str
    acknowledged: bool


class AlertListResponse(BaseModel):
    """List of system alerts."""
    alerts: list[SystemAlertResponse]
    total: int
