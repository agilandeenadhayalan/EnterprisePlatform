"""
Tests for the Analytics Service API.

Covers: hourly metrics, daily metrics, top zones, revenue trends,
driver performance, platform overview, filtering, and edge cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_hourly_metrics_returns_data(client: AsyncClient):
    """Hourly metrics endpoint returns seeded data."""
    resp = await client.get("/analytics/rides/hourly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert len(data["metrics"]) > 0
    metric = data["metrics"][0]
    assert "hour" in metric
    assert "zone_id" in metric
    assert "ride_count" in metric
    assert "total_revenue" in metric


@pytest.mark.anyio
async def test_hourly_metrics_filter_by_zone(client: AsyncClient):
    """Hourly metrics can be filtered by zone_id."""
    resp = await client.get("/analytics/rides/hourly?zone_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for metric in data["metrics"]:
        assert metric["zone_id"] == 1


@pytest.mark.anyio
async def test_hourly_metrics_filter_by_date(client: AsyncClient):
    """Hourly metrics can be filtered by specific date."""
    resp = await client.get("/analytics/rides/hourly?date=2024-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for metric in data["metrics"]:
        assert metric["hour"].startswith("2024-01-15")


@pytest.mark.anyio
async def test_hourly_metrics_filter_by_zone_and_date(client: AsyncClient):
    """Hourly metrics can be filtered by both zone and date."""
    resp = await client.get("/analytics/rides/hourly?zone_id=7&date=2024-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 24  # 24 hours for one zone on one day
    for metric in data["metrics"]:
        assert metric["zone_id"] == 7


@pytest.mark.anyio
async def test_hourly_metrics_nonexistent_zone(client: AsyncClient):
    """Filtering by a zone that does not exist returns empty."""
    resp = await client.get("/analytics/rides/hourly?zone_id=9999")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["metrics"] == []


@pytest.mark.anyio
async def test_daily_metrics_returns_data(client: AsyncClient):
    """Daily metrics endpoint returns seeded data."""
    resp = await client.get("/analytics/rides/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    metric = data["metrics"][0]
    assert "date" in metric
    assert "ride_count" in metric
    assert "unique_drivers" in metric


@pytest.mark.anyio
async def test_daily_metrics_filter_by_zone(client: AsyncClient):
    """Daily metrics can be filtered by zone_id."""
    resp = await client.get("/analytics/rides/daily?zone_id=7")
    assert resp.status_code == 200
    data = resp.json()
    for metric in data["metrics"]:
        assert metric["zone_id"] == 7


@pytest.mark.anyio
async def test_daily_metrics_filter_by_date_range(client: AsyncClient):
    """Daily metrics can be filtered by start and end date."""
    resp = await client.get("/analytics/rides/daily?start_date=2024-01-15&end_date=2024-01-17")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for metric in data["metrics"]:
        assert "2024-01-15" <= metric["date"] <= "2024-01-17"


@pytest.mark.anyio
async def test_top_zones_by_rides(client: AsyncClient):
    """Top zones ranked by ride count."""
    resp = await client.get("/analytics/zones/top?metric=rides&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "rides"
    assert data["total"] == 5
    rankings = data["rankings"]
    assert rankings[0]["rank"] == 1
    # Verify descending order
    for i in range(len(rankings) - 1):
        assert rankings[i]["ride_count"] >= rankings[i + 1]["ride_count"]


@pytest.mark.anyio
async def test_top_zones_by_revenue(client: AsyncClient):
    """Top zones ranked by revenue."""
    resp = await client.get("/analytics/zones/top?metric=revenue&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "revenue"
    assert data["total"] == 3
    rankings = data["rankings"]
    for i in range(len(rankings) - 1):
        assert rankings[i]["total_revenue"] >= rankings[i + 1]["total_revenue"]


@pytest.mark.anyio
async def test_revenue_trends_daily(client: AsyncClient):
    """Revenue trends at daily granularity."""
    resp = await client.get("/analytics/revenue/trends?granularity=daily")
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "daily"
    assert data["total"] > 0
    trend = data["trends"][0]
    assert "period" in trend
    assert "total_revenue" in trend
    assert "revenue_change_pct" in trend


@pytest.mark.anyio
async def test_revenue_trends_monthly(client: AsyncClient):
    """Revenue trends at monthly granularity."""
    resp = await client.get("/analytics/revenue/trends?granularity=monthly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "monthly"
    assert data["total"] > 0


@pytest.mark.anyio
async def test_revenue_trends_hourly(client: AsyncClient):
    """Revenue trends at hourly granularity."""
    resp = await client.get("/analytics/revenue/trends?granularity=hourly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "hourly"
    assert data["total"] > 0


@pytest.mark.anyio
async def test_driver_performance(client: AsyncClient):
    """Driver performance endpoint returns seeded driver data."""
    resp = await client.get("/analytics/drivers/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15  # 15 seeded drivers
    driver = data["drivers"][0]
    assert "driver_id" in driver
    assert "driver_name" in driver
    assert "total_rides" in driver
    assert "avg_rating" in driver
    assert "completion_rate" in driver


@pytest.mark.anyio
async def test_platform_overview(client: AsyncClient):
    """Platform overview returns aggregated metrics."""
    resp = await client.get("/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rides"] > 0
    assert data["total_revenue"] > 0
    assert data["active_drivers"] == 15
    assert data["avg_fare"] > 0
    assert data["total_zones_served"] > 0
    assert data["avg_trips_per_driver"] > 0


@pytest.mark.anyio
async def test_top_zones_default_limit(client: AsyncClient):
    """Top zones with default limit returns 10 results."""
    resp = await client.get("/analytics/zones/top")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10


@pytest.mark.anyio
async def test_revenue_trends_with_date_filter(client: AsyncClient):
    """Revenue trends filtered by date range."""
    resp = await client.get(
        "/analytics/revenue/trends?granularity=daily&start_date=2024-01-15&end_date=2024-01-17"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for trend in data["trends"]:
        assert "2024-01-15" <= trend["period"] <= "2024-01-17"
