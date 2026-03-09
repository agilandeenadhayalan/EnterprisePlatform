"""
Domain models for the analytics service.

Represents aggregated ride metrics, zone rankings, revenue trends,
driver performance, and platform overview data.
"""

from datetime import datetime, date
from typing import Optional


class HourlyRideMetric:
    """Aggregated ride metrics for a single hour."""

    def __init__(
        self,
        hour: str,
        zone_id: int,
        zone_name: str,
        ride_count: int,
        total_revenue: float,
        avg_fare: float,
        avg_duration_minutes: float,
        avg_distance_miles: float,
    ):
        self.hour = hour
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.ride_count = ride_count
        self.total_revenue = total_revenue
        self.avg_fare = avg_fare
        self.avg_duration_minutes = avg_duration_minutes
        self.avg_distance_miles = avg_distance_miles

    def to_dict(self) -> dict:
        return {
            "hour": self.hour,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "ride_count": self.ride_count,
            "total_revenue": self.total_revenue,
            "avg_fare": self.avg_fare,
            "avg_duration_minutes": self.avg_duration_minutes,
            "avg_distance_miles": self.avg_distance_miles,
        }


class DailyRideMetric:
    """Aggregated ride metrics for a single day."""

    def __init__(
        self,
        date: str,
        zone_id: int,
        zone_name: str,
        ride_count: int,
        total_revenue: float,
        avg_fare: float,
        peak_hour: int,
        unique_drivers: int,
    ):
        self.date = date
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.ride_count = ride_count
        self.total_revenue = total_revenue
        self.avg_fare = avg_fare
        self.peak_hour = peak_hour
        self.unique_drivers = unique_drivers

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "ride_count": self.ride_count,
            "total_revenue": self.total_revenue,
            "avg_fare": self.avg_fare,
            "peak_hour": self.peak_hour,
            "unique_drivers": self.unique_drivers,
        }


class ZoneRanking:
    """Zone ranked by a specific metric (rides or revenue)."""

    def __init__(
        self,
        rank: int,
        zone_id: int,
        zone_name: str,
        ride_count: int,
        total_revenue: float,
        avg_fare: float,
    ):
        self.rank = rank
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.ride_count = ride_count
        self.total_revenue = total_revenue
        self.avg_fare = avg_fare

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "ride_count": self.ride_count,
            "total_revenue": self.total_revenue,
            "avg_fare": self.avg_fare,
        }


class RevenueTrend:
    """Revenue data point in a time series."""

    def __init__(
        self,
        period: str,
        total_revenue: float,
        ride_count: int,
        avg_fare: float,
        revenue_change_pct: float,
    ):
        self.period = period
        self.total_revenue = total_revenue
        self.ride_count = ride_count
        self.avg_fare = avg_fare
        self.revenue_change_pct = revenue_change_pct

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "total_revenue": self.total_revenue,
            "ride_count": self.ride_count,
            "avg_fare": self.avg_fare,
            "revenue_change_pct": self.revenue_change_pct,
        }


class DriverPerformance:
    """Performance metrics for a driver."""

    def __init__(
        self,
        driver_id: str,
        driver_name: str,
        total_rides: int,
        total_revenue: float,
        avg_rating: float,
        avg_trip_duration_minutes: float,
        completion_rate: float,
        online_hours: float,
    ):
        self.driver_id = driver_id
        self.driver_name = driver_name
        self.total_rides = total_rides
        self.total_revenue = total_revenue
        self.avg_rating = avg_rating
        self.avg_trip_duration_minutes = avg_trip_duration_minutes
        self.completion_rate = completion_rate
        self.online_hours = online_hours

    def to_dict(self) -> dict:
        return {
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "total_rides": self.total_rides,
            "total_revenue": self.total_revenue,
            "avg_rating": self.avg_rating,
            "avg_trip_duration_minutes": self.avg_trip_duration_minutes,
            "completion_rate": self.completion_rate,
            "online_hours": self.online_hours,
        }


class PlatformOverview:
    """High-level platform summary metrics."""

    def __init__(
        self,
        total_rides: int,
        total_revenue: float,
        active_drivers: int,
        avg_fare: float,
        total_zones_served: int,
        avg_trips_per_driver: float,
    ):
        self.total_rides = total_rides
        self.total_revenue = total_revenue
        self.active_drivers = active_drivers
        self.avg_fare = avg_fare
        self.total_zones_served = total_zones_served
        self.avg_trips_per_driver = avg_trips_per_driver

    def to_dict(self) -> dict:
        return {
            "total_rides": self.total_rides,
            "total_revenue": self.total_revenue,
            "active_drivers": self.active_drivers,
            "avg_fare": self.avg_fare,
            "total_zones_served": self.total_zones_served,
            "avg_trips_per_driver": self.avg_trips_per_driver,
        }
