"""
Tests for the Region Router Service API.

Covers: region CRUD, geo-routing, latency-based routing, weighted routing,
        routing table, latency checks, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_REGION = {
    "name": "US East",
    "code": "us-east-1",
    "endpoint": "https://us-east-1.api.example.com",
    "status": "active",
    "is_primary": True,
    "latitude": 39.0438,
    "longitude": -77.4874,
}

SAMPLE_REGION_2 = {
    "name": "EU West",
    "code": "eu-west-1",
    "endpoint": "https://eu-west-1.api.example.com",
    "status": "active",
    "is_primary": False,
    "latitude": 53.3498,
    "longitude": -6.2603,
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_region(client: AsyncClient):
    """Register a new region."""
    resp = await client.post("/regions", json=SAMPLE_REGION)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "US East"
    assert data["code"] == "us-east-1"
    assert data["is_primary"] is True
    assert "id" in data


@pytest.mark.anyio
async def test_list_regions(client: AsyncClient):
    """List all regions."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.get("/regions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_region(client: AsyncClient):
    """Get a specific region by code."""
    await client.post("/regions", json=SAMPLE_REGION)

    resp = await client.get("/regions/us-east-1")
    assert resp.status_code == 200
    assert resp.json()["code"] == "us-east-1"


@pytest.mark.anyio
async def test_get_region_not_found(client: AsyncClient):
    """Getting non-existent region returns 404."""
    resp = await client.get("/regions/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_region(client: AsyncClient):
    """Update a region's configuration."""
    await client.post("/regions", json=SAMPLE_REGION)

    resp = await client.patch("/regions/us-east-1", json={
        "status": "degraded",
        "endpoint": "https://us-east-1-backup.api.example.com",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"
    assert resp.json()["endpoint"] == "https://us-east-1-backup.api.example.com"


@pytest.mark.anyio
async def test_update_region_not_found(client: AsyncClient):
    """Updating non-existent region returns 404."""
    resp = await client.patch("/regions/nonexistent", json={"status": "offline"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_route_geo(client: AsyncClient):
    """Route request using geo strategy (closest region)."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    # Request from New York area — should route to us-east-1
    resp = await client.post("/regions/route", json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "strategy": "geo",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["region_code"] == "us-east-1"
    assert data["distance_km"] > 0
    assert data["score"] > 0


@pytest.mark.anyio
async def test_route_latency(client: AsyncClient):
    """Route request using latency strategy."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.post("/regions/route", json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "strategy": "latency",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "region_code" in data
    assert data["latency_ms"] > 0


@pytest.mark.anyio
async def test_route_weighted(client: AsyncClient):
    """Route request using weighted strategy."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.post("/regions/route", json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "strategy": "weighted",
    })
    assert resp.status_code == 200
    assert resp.json()["score"] > 0


@pytest.mark.anyio
async def test_route_no_active_regions(client: AsyncClient):
    """Routing with no active regions returns 404."""
    await client.post("/regions", json={**SAMPLE_REGION, "status": "offline"})

    resp = await client.post("/regions/route", json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "strategy": "geo",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_routing_table(client: AsyncClient):
    """Get routing table."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.get("/regions/routing-table")
    assert resp.status_code == 200
    table = resp.json()
    assert len(table) == 2
    codes = [entry["region_code"] for entry in table]
    assert "us-east-1" in codes


@pytest.mark.anyio
async def test_routing_table_empty(client: AsyncClient):
    """Routing table returns empty list when no regions."""
    resp = await client.get("/regions/routing-table")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_latency_check(client: AsyncClient):
    """Check latency to all regions."""
    await client.post("/regions", json=SAMPLE_REGION)
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.post("/regions/latency-check")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all("latency_ms" in r for r in results)
    assert all(r["latency_ms"] > 0 for r in results)


@pytest.mark.anyio
async def test_create_region_with_metadata(client: AsyncClient):
    """Create region with additional metadata."""
    region = {**SAMPLE_REGION, "metadata": {"provider": "aws", "tier": "premium"}}
    resp = await client.post("/regions", json=region)
    assert resp.status_code == 201
    assert resp.json()["metadata"]["provider"] == "aws"


@pytest.mark.anyio
async def test_route_skips_offline_regions(client: AsyncClient):
    """Routing skips offline regions."""
    await client.post("/regions", json={**SAMPLE_REGION, "status": "offline"})
    await client.post("/regions", json=SAMPLE_REGION_2)

    resp = await client.post("/regions/route", json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "strategy": "geo",
    })
    assert resp.status_code == 200
    assert resp.json()["region_code"] == "eu-west-1"
