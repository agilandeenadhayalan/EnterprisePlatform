"""
Reporting repository — in-memory report store.

Stores report definitions and generated reports. In production,
this would use PostgreSQL for report metadata and MinIO for report artifacts.
"""

import uuid
import random
from datetime import datetime
from typing import Any, Optional

from models import Report, ReportResult, ReportType


# Available report types
REPORT_TYPES = [
    ReportType(
        type_id="daily_summary",
        name="Daily Summary",
        description="Summary of daily ride activity including total rides, revenue, and top zones",
        required_params=["date"],
        optional_params=["zone_id"],
        supported_formats=["json", "csv", "pdf"],
    ),
    ReportType(
        type_id="weekly_zone_analysis",
        name="Weekly Zone Analysis",
        description="Detailed zone-by-zone analysis of ride patterns over a week",
        required_params=["start_date"],
        optional_params=["end_date", "zone_ids"],
        supported_formats=["json", "csv"],
    ),
    ReportType(
        type_id="driver_scorecard",
        name="Driver Scorecard",
        description="Individual driver performance scorecard with ratings and metrics",
        required_params=["driver_id"],
        optional_params=["start_date", "end_date"],
        supported_formats=["json", "pdf"],
    ),
    ReportType(
        type_id="revenue_report",
        name="Revenue Report",
        description="Detailed revenue breakdown by zone, time period, and payment method",
        required_params=["start_date", "end_date"],
        optional_params=["zone_id", "granularity"],
        supported_formats=["json", "csv", "pdf"],
    ),
    ReportType(
        type_id="trip_patterns",
        name="Trip Patterns",
        description="Analysis of trip patterns including popular routes, peak hours, and duration distributions",
        required_params=[],
        optional_params=["start_date", "end_date", "zone_id"],
        supported_formats=["json", "csv"],
    ),
]


def _generate_mock_result(report_type: str, parameters: dict[str, Any]) -> ReportResult:
    """Generate mock report data based on report type."""
    rng = random.Random(hash(report_type + str(parameters)))

    if report_type == "daily_summary":
        return ReportResult(
            summary={
                "date": parameters.get("date", "2024-01-15"),
                "total_rides": rng.randint(5000, 50000),
                "total_revenue": round(rng.uniform(50000, 500000), 2),
                "avg_fare": round(rng.uniform(12.0, 35.0), 2),
                "top_zones": [
                    {"zone_id": 161, "zone_name": "Midtown Center", "rides": rng.randint(500, 2000)},
                    {"zone_id": 237, "zone_name": "Upper East Side South", "rides": rng.randint(400, 1500)},
                    {"zone_id": 236, "zone_name": "Upper East Side North", "rides": rng.randint(300, 1200)},
                ],
                "peak_hour": rng.choice([8, 9, 17, 18]),
                "active_drivers": rng.randint(200, 800),
            },
            row_count=rng.randint(5000, 50000),
        )
    elif report_type == "weekly_zone_analysis":
        return ReportResult(
            summary={
                "start_date": parameters.get("start_date", "2024-01-15"),
                "end_date": parameters.get("end_date", "2024-01-21"),
                "zones_analyzed": rng.randint(50, 265),
                "total_rides": rng.randint(30000, 300000),
                "busiest_zone": {"zone_id": 161, "zone_name": "Midtown Center"},
                "quietest_zone": {"zone_id": 211, "zone_name": "Rikers Island"},
                "avg_rides_per_zone": rng.randint(100, 1500),
            },
            row_count=rng.randint(100, 500),
        )
    elif report_type == "driver_scorecard":
        return ReportResult(
            summary={
                "driver_id": parameters.get("driver_id", "drv-0001"),
                "total_rides": rng.randint(50, 500),
                "avg_rating": round(rng.uniform(3.5, 5.0), 2),
                "completion_rate": round(rng.uniform(0.85, 0.99), 3),
                "total_revenue": round(rng.uniform(1000, 15000), 2),
                "avg_trip_duration_minutes": round(rng.uniform(10.0, 30.0), 1),
                "rank_percentile": rng.randint(1, 100),
            },
            row_count=1,
        )
    elif report_type == "revenue_report":
        return ReportResult(
            summary={
                "start_date": parameters.get("start_date", "2024-01-01"),
                "end_date": parameters.get("end_date", "2024-01-31"),
                "total_revenue": round(rng.uniform(500000, 5000000), 2),
                "by_zone_count": rng.randint(50, 265),
                "avg_daily_revenue": round(rng.uniform(15000, 150000), 2),
                "peak_revenue_day": "2024-01-19",
                "lowest_revenue_day": "2024-01-02",
            },
            row_count=rng.randint(100, 1000),
        )
    else:  # trip_patterns
        return ReportResult(
            summary={
                "total_trips_analyzed": rng.randint(10000, 100000),
                "avg_trip_distance_miles": round(rng.uniform(2.0, 8.0), 1),
                "avg_trip_duration_minutes": round(rng.uniform(10.0, 25.0), 1),
                "most_popular_route": {
                    "origin_zone": "Midtown Center",
                    "destination_zone": "JFK Airport",
                    "trip_count": rng.randint(100, 1000),
                },
                "peak_hours": [8, 9, 17, 18, 19],
                "weekend_vs_weekday_ratio": round(rng.uniform(0.4, 0.7), 2),
            },
            row_count=rng.randint(500, 5000),
        )


class ReportingRepository:
    """In-memory report storage."""

    def __init__(self):
        self._reports: dict[str, Report] = {}

    def get_report_types(self) -> list[ReportType]:
        """Get all available report types."""
        return REPORT_TYPES

    def get_report_type(self, type_id: str) -> Optional[ReportType]:
        """Get a specific report type by ID."""
        for rt in REPORT_TYPES:
            if rt.type_id == type_id:
                return rt
        return None

    def create_report(
        self,
        report_type: str,
        parameters: dict[str, Any],
        format: str = "json",
    ) -> Report:
        """Generate a new report (mock: completes immediately)."""
        report_id = str(uuid.uuid4())

        # Generate mock result data
        result = _generate_mock_result(report_type, parameters)

        report = Report(
            id=report_id,
            report_type=report_type,
            status="completed",
            parameters=parameters,
            format=format,
            result=result,
            completed_at=datetime.utcnow(),
        )
        self._reports[report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[Report]:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[Report]:
        """List reports with optional filtering."""
        reports = list(self._reports.values())

        if report_type:
            reports = [r for r in reports if r.report_type == report_type]

        if status:
            reports = [r for r in reports if r.status == status]

        return sorted(reports, key=lambda r: r.created_at, reverse=True)

    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False


# Singleton repository instance
repo = ReportingRepository()
