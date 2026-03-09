"""
Tests for the Dashboard Service API.

Covers: overview, realtime metrics, zone heatmap, trends, alerts, and edge cases.
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
async def test_dashboard_overview(client: AsyncClient):
    """Overview endpoint returns platform metrics with growth percentages."""
    resp = await client.get("/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rides"] > 0
    assert data["total_revenue"] > 0
    assert data["active_drivers"] > 0
    assert data["avg_fare"] > 0
    assert "rides_growth_pct" in data
    assert "revenue_growth_pct" in data
    assert "drivers_growth_pct" in data


@pytest.mark.anyio
async def test_realtime_metrics(client: AsyncClient):
    """Realtime endpoint returns live platform data."""
    resp = await client.get("/dashboard/realtime")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rides_in_progress"] > 0
    assert data["active_drivers"] > 0
    assert "queued_requests" in data
    assert "avg_wait_time_seconds" in data
    assert len(data["recent_events"]) > 0


@pytest.mark.anyio
async def test_realtime_events_have_timestamps(client: AsyncClient):
    """Real-time events include timestamps."""
    resp = await client.get("/dashboard/realtime")
    events = resp.json()["recent_events"]
    for event in events:
        assert "timestamp" in event
        assert "type" in event


@pytest.mark.anyio
async def test_zone_heatmap(client: AsyncClient):
    """Zone heatmap returns zone data with coordinates."""
    resp = await client.get("/dashboard/zones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    zone = data["zones"][0]
    assert "zone_id" in zone
    assert "zone_name" in zone
    assert "ride_count" in zone
    assert "revenue" in zone
    assert "avg_fare" in zone
    assert "lat" in zone
    assert "lng" in zone


@pytest.mark.anyio
async def test_zone_heatmap_coordinates_valid(client: AsyncClient):
    """Zone heatmap coordinates are within NYC bounds."""
    resp = await client.get("/dashboard/zones")
    for zone in resp.json()["zones"]:
        assert 40.4 <= zone["lat"] <= 41.0, f"Latitude out of bounds for {zone['zone_name']}"
        assert -74.3 <= zone["lng"] <= -73.7, f"Longitude out of bounds for {zone['zone_name']}"


@pytest.mark.anyio
async def test_trends_default_7d(client: AsyncClient):
    """Trends endpoint returns 7-day data by default."""
    resp = await client.get("/dashboard/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    for dp in data["data_points"]:
        assert "period" in dp
        assert "ride_count" in dp
        assert "revenue" in dp


@pytest.mark.anyio
async def test_trends_24h(client: AsyncClient):
    """Trends endpoint returns 24-hour data."""
    resp = await client.get("/dashboard/trends?period=24h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 24


@pytest.mark.anyio
async def test_trends_30d(client: AsyncClient):
    """Trends endpoint returns 30-day data."""
    resp = await client.get("/dashboard/trends?period=30d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 30


@pytest.mark.anyio
async def test_alerts(client: AsyncClient):
    """Alerts endpoint returns active system alerts."""
    resp = await client.get("/dashboard/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    alert = data["alerts"][0]
    assert "id" in alert
    assert "severity" in alert
    assert "category" in alert
    assert "message" in alert
    assert "created_at" in alert


@pytest.mark.anyio
async def test_alerts_have_valid_severities(client: AsyncClient):
    """Alerts have valid severity levels."""
    resp = await client.get("/dashboard/alerts")
    valid_severities = {"critical", "warning", "info"}
    for alert in resp.json()["alerts"]:
        assert alert["severity"] in valid_severities


@pytest.mark.anyio
async def test_alerts_have_valid_categories(client: AsyncClient):
    """Alerts have valid category values."""
    resp = await client.get("/dashboard/alerts")
    valid_categories = {"data_quality", "etl", "capacity", "system"}
    for alert in resp.json()["alerts"]:
        assert alert["category"] in valid_categories
