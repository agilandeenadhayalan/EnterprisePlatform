"""
Dashboard Service — FastAPI application.

Backend-for-frontend for the analytics dashboard. Aggregates data from
multiple sources and formats it for dashboard UI consumption.

ROUTES:
  GET  /dashboard/overview   — Platform overview metrics (rides, revenue, growth %)
  GET  /dashboard/realtime   — Real-time metrics (rides in progress, active drivers)
  GET  /dashboard/zones      — Zone heatmap data (zone_id, name, ride_count, revenue)
  GET  /dashboard/trends     — Time series data for charts (ride_count, revenue)
  GET  /dashboard/alerts     — Active system alerts (data quality, ETL, capacity)
  GET  /health               — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Query

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Backend-for-frontend for the analytics dashboard",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/dashboard/overview", response_model=schemas.DashboardOverviewResponse)
async def dashboard_overview():
    """Platform overview metrics — total rides, revenue, active drivers, avg fare, growth percentages."""
    overview = repository.repo.get_overview()
    return schemas.DashboardOverviewResponse(**overview.to_dict())


@app.get("/dashboard/realtime", response_model=schemas.RealtimeMetricsResponse)
async def realtime_metrics():
    """Real-time metrics — rides in progress, active drivers, recent events."""
    metrics = repository.repo.get_realtime_metrics()
    return schemas.RealtimeMetricsResponse(**metrics.to_dict())


@app.get("/dashboard/zones", response_model=schemas.ZoneHeatmapResponse)
async def zone_heatmap():
    """Zone heatmap data — zone_id, name, ride_count, revenue, avg_fare, coordinates."""
    zones = repository.repo.get_zone_heatmap()
    return schemas.ZoneHeatmapResponse(
        zones=[schemas.ZoneHeatmapEntryResponse(**z.to_dict()) for z in zones],
        total=len(zones),
    )


@app.get("/dashboard/trends", response_model=schemas.TrendDataResponse)
async def trend_data(
    period: str = Query(default="7d", description="Time period: 24h, 7d, or 30d"),
):
    """Time series data for charts — ride_count and revenue over time periods."""
    data_points = repository.repo.get_trends(period=period)
    return schemas.TrendDataResponse(
        data_points=[schemas.TrendDataPointResponse(**dp.to_dict()) for dp in data_points],
        total=len(data_points),
    )


@app.get("/dashboard/alerts", response_model=schemas.AlertListResponse)
async def system_alerts():
    """Active system alerts — data quality, ETL failures, capacity warnings."""
    alerts = repository.repo.get_alerts()
    return schemas.AlertListResponse(
        alerts=[schemas.SystemAlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
    )
