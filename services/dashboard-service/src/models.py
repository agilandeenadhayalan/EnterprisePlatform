"""
Domain models for the dashboard service.

Represents dashboard overview, real-time metrics, zone heatmap data,
trend data, and system alerts.
"""

from datetime import datetime
from typing import Any, Optional


class DashboardOverview:
    """Platform overview metrics for the dashboard."""

    def __init__(
        self,
        total_rides: int,
        total_revenue: float,
        active_drivers: int,
        avg_fare: float,
        rides_growth_pct: float,
        revenue_growth_pct: float,
        drivers_growth_pct: float,
    ):
        self.total_rides = total_rides
        self.total_revenue = total_revenue
        self.active_drivers = active_drivers
        self.avg_fare = avg_fare
        self.rides_growth_pct = rides_growth_pct
        self.revenue_growth_pct = revenue_growth_pct
        self.drivers_growth_pct = drivers_growth_pct

    def to_dict(self) -> dict:
        return {
            "total_rides": self.total_rides,
            "total_revenue": self.total_revenue,
            "active_drivers": self.active_drivers,
            "avg_fare": self.avg_fare,
            "rides_growth_pct": self.rides_growth_pct,
            "revenue_growth_pct": self.revenue_growth_pct,
            "drivers_growth_pct": self.drivers_growth_pct,
        }


class RealtimeMetrics:
    """Real-time platform metrics."""

    def __init__(
        self,
        rides_in_progress: int,
        active_drivers: int,
        queued_requests: int,
        avg_wait_time_seconds: float,
        recent_events: list[dict[str, Any]],
    ):
        self.rides_in_progress = rides_in_progress
        self.active_drivers = active_drivers
        self.queued_requests = queued_requests
        self.avg_wait_time_seconds = avg_wait_time_seconds
        self.recent_events = recent_events

    def to_dict(self) -> dict:
        return {
            "rides_in_progress": self.rides_in_progress,
            "active_drivers": self.active_drivers,
            "queued_requests": self.queued_requests,
            "avg_wait_time_seconds": self.avg_wait_time_seconds,
            "recent_events": self.recent_events,
        }


class ZoneHeatmapEntry:
    """Zone data for heatmap visualization."""

    def __init__(
        self,
        zone_id: int,
        zone_name: str,
        ride_count: int,
        revenue: float,
        avg_fare: float,
        lat: float,
        lng: float,
    ):
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.ride_count = ride_count
        self.revenue = revenue
        self.avg_fare = avg_fare
        self.lat = lat
        self.lng = lng

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "ride_count": self.ride_count,
            "revenue": self.revenue,
            "avg_fare": self.avg_fare,
            "lat": self.lat,
            "lng": self.lng,
        }


class TrendDataPoint:
    """A single data point in a time series trend."""

    def __init__(
        self,
        period: str,
        ride_count: int,
        revenue: float,
    ):
        self.period = period
        self.ride_count = ride_count
        self.revenue = revenue

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "ride_count": self.ride_count,
            "revenue": self.revenue,
        }


class SystemAlert:
    """An active system alert."""

    def __init__(
        self,
        id: str,
        severity: str,
        category: str,
        message: str,
        created_at: Optional[str] = None,
        acknowledged: bool = False,
    ):
        self.id = id
        self.severity = severity  # critical, warning, info
        self.category = category  # data_quality, etl, capacity, system
        self.message = message
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.acknowledged = acknowledged

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
        }
