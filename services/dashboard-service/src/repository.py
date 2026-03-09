"""
Dashboard repository — in-memory pre-seeded dashboard data.

Provides data for the analytics dashboard BFF. In production, this would
aggregate from multiple services (analytics, ride, driver) and cache in Redis.
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from models import (
    DashboardOverview,
    RealtimeMetrics,
    ZoneHeatmapEntry,
    TrendDataPoint,
    SystemAlert,
)

# Sample NYC zone coordinates for heatmap
_ZONE_COORDS = {
    7: ("Astoria", 40.7720, -73.9073),
    43: ("Central Harlem", 40.8116, -73.9465),
    45: ("Chinatown", 40.7158, -73.9970),
    48: ("Clinton East", 40.7614, -73.9923),
    68: ("East Chelsea", 40.7434, -73.9926),
    79: ("East Village", 40.7265, -73.9815),
    87: ("Financial District North", 40.7086, -74.0093),
    90: ("Flatiron", 40.7395, -73.9903),
    100: ("Garment District", 40.7536, -73.9888),
    107: ("Gramercy", 40.7367, -73.9844),
    113: ("Greenwich Village North", 40.7336, -73.9986),
    125: ("Hudson Sq", 40.7265, -74.0077),
    137: ("Kips Bay", 40.7397, -73.9790),
    140: ("Lenox Hill East", 40.7660, -73.9605),
    141: ("Lenox Hill West", 40.7680, -73.9645),
    142: ("Lincoln Square East", 40.7726, -73.9827),
    143: ("Lincoln Square West", 40.7746, -73.9867),
    148: ("Lower East Side", 40.7151, -73.9844),
    161: ("Midtown Center", 40.7549, -73.9840),
    162: ("Midtown East", 40.7527, -73.9713),
    163: ("Midtown North", 40.7626, -73.9780),
    164: ("Midtown South", 40.7484, -73.9848),
    170: ("Murray Hill", 40.7475, -73.9774),
    186: ("Penn Station/Madison Sq West", 40.7484, -73.9932),
    231: ("Times Sq/Theatre District", 40.7580, -73.9855),
    232: ("TriBeCa/Civic Center", 40.7163, -74.0086),
    236: ("Upper East Side North", 40.7736, -73.9566),
    237: ("Upper East Side South", 40.7659, -73.9629),
    238: ("Upper West Side North", 40.7870, -73.9754),
    239: ("Upper West Side South", 40.7811, -73.9784),
    246: ("West Chelsea/Hudson Yards", 40.7496, -74.0023),
    249: ("West Village", 40.7336, -74.0027),
    261: ("World Trade Center", 40.7118, -74.0131),
}


class DashboardRepository:
    """In-memory dashboard data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._alerts: list[SystemAlert] = []
        self._rng = random.Random(42)

        if seed:
            self._seed_alerts()

    def _seed_alerts(self):
        """Pre-populate with sample system alerts."""
        alerts_data = [
            ("warning", "data_quality", "Missing GPS coordinates in 2.3% of ride events for zone 211"),
            ("critical", "etl", "ETL pipeline postgres-to-clickhouse delayed by 15 minutes"),
            ("info", "capacity", "Driver availability in zone 161 (Midtown) above 95th percentile"),
            ("warning", "data_quality", "Duplicate ride IDs detected in last batch ingestion (0.1% rate)"),
            ("info", "system", "ClickHouse materialized view ride_hourly_mv refreshed successfully"),
        ]
        for severity, category, message in alerts_data:
            self._alerts.append(SystemAlert(
                id=str(uuid.uuid4()),
                severity=severity,
                category=category,
                message=message,
            ))

    def get_overview(self) -> DashboardOverview:
        """Get platform overview metrics with growth percentages."""
        return DashboardOverview(
            total_rides=148523,
            total_revenue=3247891.50,
            active_drivers=342,
            avg_fare=21.87,
            rides_growth_pct=12.4,
            revenue_growth_pct=8.7,
            drivers_growth_pct=3.2,
        )

    def get_realtime_metrics(self) -> RealtimeMetrics:
        """Get real-time platform metrics."""
        return RealtimeMetrics(
            rides_in_progress=127,
            active_drivers=198,
            queued_requests=34,
            avg_wait_time_seconds=245.0,
            recent_events=[
                {"type": "ride_started", "zone": "Midtown Center", "timestamp": "2024-01-15T14:32:10Z"},
                {"type": "ride_completed", "zone": "Upper East Side South", "timestamp": "2024-01-15T14:31:45Z"},
                {"type": "driver_online", "driver_id": "drv-0042", "timestamp": "2024-01-15T14:31:30Z"},
                {"type": "surge_activated", "zone": "Times Sq/Theatre District", "multiplier": 1.5, "timestamp": "2024-01-15T14:30:00Z"},
                {"type": "ride_started", "zone": "Financial District North", "timestamp": "2024-01-15T14:29:50Z"},
            ],
        )

    def get_zone_heatmap(self) -> list[ZoneHeatmapEntry]:
        """Get zone heatmap data for visualization."""
        entries = []
        for zone_id, (name, lat, lng) in _ZONE_COORDS.items():
            ride_count = self._rng.randint(50, 2000)
            avg_fare = round(self._rng.uniform(10.0, 40.0), 2)
            entries.append(ZoneHeatmapEntry(
                zone_id=zone_id,
                zone_name=name,
                ride_count=ride_count,
                revenue=round(ride_count * avg_fare, 2),
                avg_fare=avg_fare,
                lat=lat,
                lng=lng,
            ))
        return entries

    def get_trends(self, period: str = "7d") -> list[TrendDataPoint]:
        """Get time series trend data for charts."""
        data_points = []

        if period == "24h":
            # Hourly data for last 24 hours
            for hour in range(24):
                ride_count = self._rng.randint(200, 2000)
                avg_fare = self._rng.uniform(15.0, 35.0)
                data_points.append(TrendDataPoint(
                    period=f"2024-01-15T{hour:02d}:00:00",
                    ride_count=ride_count,
                    revenue=round(ride_count * avg_fare, 2),
                ))
        elif period == "30d":
            # Daily data for 30 days
            for day in range(1, 31):
                ride_count = self._rng.randint(3000, 25000)
                avg_fare = self._rng.uniform(18.0, 28.0)
                data_points.append(TrendDataPoint(
                    period=f"2024-01-{day:02d}",
                    ride_count=ride_count,
                    revenue=round(ride_count * avg_fare, 2),
                ))
        else:  # 7d default
            for day in range(15, 22):
                ride_count = self._rng.randint(5000, 30000)
                avg_fare = self._rng.uniform(18.0, 28.0)
                data_points.append(TrendDataPoint(
                    period=f"2024-01-{day:02d}",
                    ride_count=ride_count,
                    revenue=round(ride_count * avg_fare, 2),
                ))

        return data_points

    def get_alerts(self) -> list[SystemAlert]:
        """Get active system alerts."""
        return self._alerts


# Singleton repository instance
repo = DashboardRepository(seed=True)
