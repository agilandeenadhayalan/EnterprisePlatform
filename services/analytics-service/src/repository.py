"""
Analytics repository — in-memory pre-seeded analytics data.

Seeds 265 NYC zones with hourly ride data for querying. In production,
this would query ClickHouse materialized views and fact tables.
"""

import random
from typing import Optional

from models import (
    HourlyRideMetric,
    DailyRideMetric,
    ZoneRanking,
    RevenueTrend,
    DriverPerformance,
    PlatformOverview,
)

# NYC zone names (sample of well-known zones)
_ZONE_NAMES = {
    1: "Newark Airport", 2: "Jamaica Bay", 3: "Allerton/Pelham Gardens",
    4: "Alphabet City", 5: "Arden Heights", 6: "Arrochar/Fort Wadsworth",
    7: "Astoria", 8: "Astoria Park", 9: "Auburndale", 10: "Baisley Park",
    12: "Battery Park", 13: "Battery Park City", 24: "Bloomingdale",
    36: "Brooklyn Heights", 37: "Brooklyn Navy Yard", 43: "Central Harlem",
    45: "Chinatown", 48: "Clinton East", 50: "Clinton West",
    68: "East Chelsea", 74: "East Harlem North", 75: "East Harlem South",
    79: "East Village", 87: "Financial District North", 88: "Financial District South",
    90: "Flatiron", 100: "Garment District", 107: "Gramercy",
    113: "Greenwich Village North", 114: "Greenwich Village South",
    125: "Hudson Sq", 137: "Kips Bay", 140: "Lenox Hill East",
    141: "Lenox Hill West", 142: "Lincoln Square East", 143: "Lincoln Square West",
    144: "Little Italy/NoLiTa", 148: "Lower East Side",
    151: "Manhattan Valley", 152: "Marble Hill", 153: "Mariners Harbor",
    158: "Meatpacking/West Village W", 161: "Midtown Center",
    162: "Midtown East", 163: "Midtown North", 164: "Midtown South",
    166: "Morningside Heights", 170: "Murray Hill",
    186: "Penn Station/Madison Sq West", 202: "Queensbridge/Ravenswood",
    209: "Ridgewood", 211: "Rikers Island", 224: "Stuy Town/PCV",
    229: "Sutton Place/Turtle Bay East", 230: "Sutton Place/Turtle Bay North",
    231: "Times Sq/Theatre District", 232: "TriBeCa/Civic Center",
    233: "Two Bridges/Seward Park", 234: "UN/Turtle Bay South",
    236: "Upper East Side North", 237: "Upper East Side South",
    238: "Upper West Side North", 239: "Upper West Side South",
    243: "Washington Heights North", 244: "Washington Heights South",
    246: "West Chelsea/Hudson Yards", 249: "West Village",
    261: "World Trade Center", 262: "Yorkville East", 263: "Yorkville West",
}


class AnalyticsRepository:
    """In-memory analytics data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._hourly_metrics: list[HourlyRideMetric] = []
        self._daily_metrics: list[DailyRideMetric] = []
        self._driver_performance: list[DriverPerformance] = []
        self._rng = random.Random(42)

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with realistic sample analytics data."""
        # Seed hourly metrics for 265 zones across 24 hours for one day
        for zone_id in range(1, 266):
            zone_name = _ZONE_NAMES.get(zone_id, f"Zone {zone_id}")
            # Manhattan zones (1-263) get more rides
            is_manhattan = zone_id in _ZONE_NAMES
            base_rides = self._rng.randint(20, 200) if is_manhattan else self._rng.randint(1, 30)

            for hour in range(24):
                # Rush hour multiplier
                if hour in (7, 8, 9, 17, 18, 19):
                    multiplier = 2.5
                elif hour in (10, 11, 12, 13, 14, 15, 16):
                    multiplier = 1.5
                elif hour in (20, 21, 22, 23):
                    multiplier = 1.2
                else:
                    multiplier = 0.3

                ride_count = max(1, int(base_rides * multiplier * self._rng.uniform(0.7, 1.3)))
                avg_fare = round(self._rng.uniform(8.0, 45.0), 2)
                total_revenue = round(ride_count * avg_fare, 2)

                self._hourly_metrics.append(HourlyRideMetric(
                    hour=f"2024-01-15T{hour:02d}:00:00",
                    zone_id=zone_id,
                    zone_name=zone_name,
                    ride_count=ride_count,
                    total_revenue=total_revenue,
                    avg_fare=avg_fare,
                    avg_duration_minutes=round(self._rng.uniform(5.0, 45.0), 1),
                    avg_distance_miles=round(self._rng.uniform(0.5, 15.0), 1),
                ))

        # Seed daily metrics for 7 days
        for day_offset in range(7):
            date_str = f"2024-01-{15 + day_offset:02d}"
            for zone_id in range(1, 266):
                zone_name = _ZONE_NAMES.get(zone_id, f"Zone {zone_id}")
                is_manhattan = zone_id in _ZONE_NAMES
                ride_count = self._rng.randint(100, 2000) if is_manhattan else self._rng.randint(5, 200)
                avg_fare = round(self._rng.uniform(10.0, 40.0), 2)

                self._daily_metrics.append(DailyRideMetric(
                    date=date_str,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    ride_count=ride_count,
                    total_revenue=round(ride_count * avg_fare, 2),
                    avg_fare=avg_fare,
                    peak_hour=self._rng.choice([8, 9, 17, 18]),
                    unique_drivers=self._rng.randint(10, max(11, ride_count // 2 + 1)),
                ))

        # Seed driver performance data
        driver_names = [
            "John Smith", "Maria Garcia", "David Kim", "Sarah Johnson",
            "Ahmed Hassan", "Lisa Chen", "James Brown", "Ana Rodriguez",
            "Wei Zhang", "Fatima Ali", "Carlos Lopez", "Priya Patel",
            "Michael O'Brien", "Yuki Tanaka", "Omar Ibrahim",
        ]
        for i, name in enumerate(driver_names):
            total_rides = self._rng.randint(50, 500)
            self._driver_performance.append(DriverPerformance(
                driver_id=f"drv-{i + 1:04d}",
                driver_name=name,
                total_rides=total_rides,
                total_revenue=round(total_rides * self._rng.uniform(15.0, 35.0), 2),
                avg_rating=round(self._rng.uniform(3.5, 5.0), 2),
                avg_trip_duration_minutes=round(self._rng.uniform(10.0, 30.0), 1),
                completion_rate=round(self._rng.uniform(0.85, 0.99), 3),
                online_hours=round(self._rng.uniform(20.0, 60.0), 1),
            ))

    def get_hourly_metrics(
        self,
        zone_id: Optional[int] = None,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[HourlyRideMetric]:
        """Query hourly ride metrics with optional filters."""
        results = self._hourly_metrics

        if zone_id is not None:
            results = [m for m in results if m.zone_id == zone_id]

        if date is not None:
            results = [m for m in results if m.hour.startswith(date)]

        if start_date is not None:
            results = [m for m in results if m.hour >= start_date]

        if end_date is not None:
            results = [m for m in results if m.hour <= end_date + "T23:59:59"]

        return results

    def get_daily_metrics(
        self,
        zone_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[DailyRideMetric]:
        """Query daily ride aggregates with optional filters."""
        results = self._daily_metrics

        if zone_id is not None:
            results = [m for m in results if m.zone_id == zone_id]

        if start_date is not None:
            results = [m for m in results if m.date >= start_date]

        if end_date is not None:
            results = [m for m in results if m.date <= end_date]

        return results

    def get_top_zones(
        self,
        metric: str = "rides",
        limit: int = 10,
    ) -> list[ZoneRanking]:
        """Get top N zones ranked by ride count or revenue."""
        # Aggregate daily metrics by zone
        zone_agg: dict[int, dict] = {}
        for m in self._daily_metrics:
            if m.zone_id not in zone_agg:
                zone_agg[m.zone_id] = {
                    "zone_id": m.zone_id,
                    "zone_name": m.zone_name,
                    "ride_count": 0,
                    "total_revenue": 0.0,
                }
            zone_agg[m.zone_id]["ride_count"] += m.ride_count
            zone_agg[m.zone_id]["total_revenue"] += m.total_revenue

        # Sort by chosen metric
        sort_key = "ride_count" if metric == "rides" else "total_revenue"
        sorted_zones = sorted(zone_agg.values(), key=lambda z: z[sort_key], reverse=True)[:limit]

        return [
            ZoneRanking(
                rank=i + 1,
                zone_id=z["zone_id"],
                zone_name=z["zone_name"],
                ride_count=z["ride_count"],
                total_revenue=round(z["total_revenue"], 2),
                avg_fare=round(z["total_revenue"] / z["ride_count"], 2) if z["ride_count"] > 0 else 0,
            )
            for i, z in enumerate(sorted_zones)
        ]

    def get_revenue_trends(
        self,
        granularity: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[RevenueTrend]:
        """Get revenue trends over time at the specified granularity."""
        if granularity == "hourly":
            filtered = self._hourly_metrics
            if start_date:
                filtered = [m for m in filtered if m.hour >= start_date]
            if end_date:
                filtered = [m for m in filtered if m.hour <= end_date + "T23:59:59"]

            # Aggregate by hour
            hour_agg: dict[str, dict] = {}
            for m in filtered:
                if m.hour not in hour_agg:
                    hour_agg[m.hour] = {"revenue": 0.0, "rides": 0}
                hour_agg[m.hour]["revenue"] += m.total_revenue
                hour_agg[m.hour]["rides"] += m.ride_count

            sorted_hours = sorted(hour_agg.keys())
            trends = []
            prev_revenue = 0.0
            for period in sorted_hours:
                agg = hour_agg[period]
                avg_fare = round(agg["revenue"] / agg["rides"], 2) if agg["rides"] > 0 else 0
                change = round(((agg["revenue"] - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0, 2)
                trends.append(RevenueTrend(
                    period=period,
                    total_revenue=round(agg["revenue"], 2),
                    ride_count=agg["rides"],
                    avg_fare=avg_fare,
                    revenue_change_pct=change,
                ))
                prev_revenue = agg["revenue"]
            return trends

        elif granularity == "monthly":
            # Aggregate daily metrics by month
            month_agg: dict[str, dict] = {}
            filtered = self._daily_metrics
            if start_date:
                filtered = [m for m in filtered if m.date >= start_date]
            if end_date:
                filtered = [m for m in filtered if m.date <= end_date]

            for m in filtered:
                month = m.date[:7]  # "2024-01"
                if month not in month_agg:
                    month_agg[month] = {"revenue": 0.0, "rides": 0}
                month_agg[month]["revenue"] += m.total_revenue
                month_agg[month]["rides"] += m.ride_count

            sorted_months = sorted(month_agg.keys())
            trends = []
            prev_revenue = 0.0
            for period in sorted_months:
                agg = month_agg[period]
                avg_fare = round(agg["revenue"] / agg["rides"], 2) if agg["rides"] > 0 else 0
                change = round(((agg["revenue"] - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0, 2)
                trends.append(RevenueTrend(
                    period=period,
                    total_revenue=round(agg["revenue"], 2),
                    ride_count=agg["rides"],
                    avg_fare=avg_fare,
                    revenue_change_pct=change,
                ))
                prev_revenue = agg["revenue"]
            return trends

        else:  # daily
            filtered = self._daily_metrics
            if start_date:
                filtered = [m for m in filtered if m.date >= start_date]
            if end_date:
                filtered = [m for m in filtered if m.date <= end_date]

            day_agg: dict[str, dict] = {}
            for m in filtered:
                if m.date not in day_agg:
                    day_agg[m.date] = {"revenue": 0.0, "rides": 0}
                day_agg[m.date]["revenue"] += m.total_revenue
                day_agg[m.date]["rides"] += m.ride_count

            sorted_days = sorted(day_agg.keys())
            trends = []
            prev_revenue = 0.0
            for period in sorted_days:
                agg = day_agg[period]
                avg_fare = round(agg["revenue"] / agg["rides"], 2) if agg["rides"] > 0 else 0
                change = round(((agg["revenue"] - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0, 2)
                trends.append(RevenueTrend(
                    period=period,
                    total_revenue=round(agg["revenue"], 2),
                    ride_count=agg["rides"],
                    avg_fare=avg_fare,
                    revenue_change_pct=change,
                ))
                prev_revenue = agg["revenue"]
            return trends

    def get_driver_performance(self) -> list[DriverPerformance]:
        """Get all driver performance metrics."""
        return self._driver_performance

    def get_platform_overview(self) -> PlatformOverview:
        """Get platform-wide overview metrics."""
        total_rides = sum(m.ride_count for m in self._daily_metrics)
        total_revenue = sum(m.total_revenue for m in self._daily_metrics)
        active_drivers = len(self._driver_performance)
        zones_served = len(set(m.zone_id for m in self._daily_metrics))
        avg_fare = round(total_revenue / total_rides, 2) if total_rides > 0 else 0
        avg_trips = round(total_rides / active_drivers, 1) if active_drivers > 0 else 0

        return PlatformOverview(
            total_rides=total_rides,
            total_revenue=round(total_revenue, 2),
            active_drivers=active_drivers,
            avg_fare=avg_fare,
            total_zones_served=zones_served,
            avg_trips_per_driver=avg_trips,
        )


# Singleton repository instance
repo = AnalyticsRepository(seed=True)
