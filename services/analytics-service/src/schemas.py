"""
Pydantic request/response schemas for the analytics API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Response schemas ──


class HourlyRideMetricResponse(BaseModel):
    """A single hourly ride metric data point."""
    hour: str
    zone_id: int
    zone_name: str
    ride_count: int
    total_revenue: float
    avg_fare: float
    avg_duration_minutes: float
    avg_distance_miles: float


class HourlyRideMetricListResponse(BaseModel):
    """List of hourly ride metrics."""
    metrics: list[HourlyRideMetricResponse]
    total: int


class DailyRideMetricResponse(BaseModel):
    """A single daily ride metric data point."""
    date: str
    zone_id: int
    zone_name: str
    ride_count: int
    total_revenue: float
    avg_fare: float
    peak_hour: int
    unique_drivers: int


class DailyRideMetricListResponse(BaseModel):
    """List of daily ride metrics."""
    metrics: list[DailyRideMetricResponse]
    total: int


class ZoneRankingResponse(BaseModel):
    """A zone ranking entry."""
    rank: int
    zone_id: int
    zone_name: str
    ride_count: int
    total_revenue: float
    avg_fare: float


class ZoneRankingListResponse(BaseModel):
    """List of zone rankings."""
    rankings: list[ZoneRankingResponse]
    metric: str
    total: int


class RevenueTrendResponse(BaseModel):
    """A single revenue trend data point."""
    period: str
    total_revenue: float
    ride_count: int
    avg_fare: float
    revenue_change_pct: float


class RevenueTrendListResponse(BaseModel):
    """List of revenue trend data points."""
    trends: list[RevenueTrendResponse]
    granularity: str
    total: int


class DriverPerformanceResponse(BaseModel):
    """Driver performance metrics."""
    driver_id: str
    driver_name: str
    total_rides: int
    total_revenue: float
    avg_rating: float
    avg_trip_duration_minutes: float
    completion_rate: float
    online_hours: float


class DriverPerformanceListResponse(BaseModel):
    """List of driver performance entries."""
    drivers: list[DriverPerformanceResponse]
    total: int


class PlatformOverviewResponse(BaseModel):
    """Platform-wide overview metrics."""
    total_rides: int
    total_revenue: float
    active_drivers: int
    avg_fare: float
    total_zones_served: int
    avg_trips_per_driver: float
