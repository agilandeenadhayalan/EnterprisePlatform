"""
Analytics Service — FastAPI application.

Query API over ClickHouse materialized views and fact tables for ride analytics.
Provides aggregated metrics for rides, zones, revenue, drivers, and platform overview.

ROUTES:
  GET  /analytics/rides/hourly       — Hourly ride counts and revenue
  GET  /analytics/rides/daily        — Daily ride aggregates
  GET  /analytics/zones/top          — Top N zones by ride count or revenue
  GET  /analytics/revenue/trends     — Revenue trends over time
  GET  /analytics/drivers/performance — Driver performance metrics
  GET  /analytics/overview           — Platform overview (total rides, revenue, etc.)
  GET  /health                       — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

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
    description="Query API over ClickHouse materialized views and fact tables",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/analytics/rides/hourly", response_model=schemas.HourlyRideMetricListResponse)
async def hourly_ride_metrics(
    zone_id: Optional[int] = Query(default=None, description="Filter by zone ID"),
    date: Optional[str] = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
):
    """Hourly ride counts and revenue, optionally filtered by zone and date range."""
    metrics = repository.repo.get_hourly_metrics(
        zone_id=zone_id, date=date, start_date=start_date, end_date=end_date,
    )
    return schemas.HourlyRideMetricListResponse(
        metrics=[schemas.HourlyRideMetricResponse(**m.to_dict()) for m in metrics],
        total=len(metrics),
    )


@app.get("/analytics/rides/daily", response_model=schemas.DailyRideMetricListResponse)
async def daily_ride_metrics(
    zone_id: Optional[int] = Query(default=None, description="Filter by zone ID"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
):
    """Daily ride aggregates, optionally filtered by zone and date range."""
    metrics = repository.repo.get_daily_metrics(
        zone_id=zone_id, start_date=start_date, end_date=end_date,
    )
    return schemas.DailyRideMetricListResponse(
        metrics=[schemas.DailyRideMetricResponse(**m.to_dict()) for m in metrics],
        total=len(metrics),
    )


@app.get("/analytics/zones/top", response_model=schemas.ZoneRankingListResponse)
async def top_zones(
    metric: str = Query(default="rides", description="Ranking metric: rides or revenue"),
    limit: int = Query(default=10, description="Number of top zones to return"),
):
    """Top N zones ranked by ride count or revenue."""
    rankings = repository.repo.get_top_zones(metric=metric, limit=limit)
    return schemas.ZoneRankingListResponse(
        rankings=[schemas.ZoneRankingResponse(**r.to_dict()) for r in rankings],
        metric=metric,
        total=len(rankings),
    )


@app.get("/analytics/revenue/trends", response_model=schemas.RevenueTrendListResponse)
async def revenue_trends(
    granularity: str = Query(default="daily", description="Granularity: hourly, daily, or monthly"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
):
    """Revenue trends over time at the specified granularity."""
    trends = repository.repo.get_revenue_trends(
        granularity=granularity, start_date=start_date, end_date=end_date,
    )
    return schemas.RevenueTrendListResponse(
        trends=[schemas.RevenueTrendResponse(**t.to_dict()) for t in trends],
        granularity=granularity,
        total=len(trends),
    )


@app.get("/analytics/drivers/performance", response_model=schemas.DriverPerformanceListResponse)
async def driver_performance():
    """Driver performance metrics across all tracked drivers."""
    drivers = repository.repo.get_driver_performance()
    return schemas.DriverPerformanceListResponse(
        drivers=[schemas.DriverPerformanceResponse(**d.to_dict()) for d in drivers],
        total=len(drivers),
    )


@app.get("/analytics/overview", response_model=schemas.PlatformOverviewResponse)
async def platform_overview():
    """Platform overview — total rides, revenue, active drivers, avg fare."""
    overview = repository.repo.get_platform_overview()
    return schemas.PlatformOverviewResponse(**overview.to_dict())
