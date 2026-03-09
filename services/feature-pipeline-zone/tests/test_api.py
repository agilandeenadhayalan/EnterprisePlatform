"""
Tests for the Feature Pipeline Zone service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_get_zone_features(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_A1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_id"] == "zone_A1"
    assert "zone_demand_last_hour" in data["features"]
    assert "zone_avg_fare" in data["features"]
    assert "zone_supply_density" in data["features"]


@pytest.mark.anyio
async def test_get_zone_features_not_found(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_ZZ")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_zone_features_all_fields(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_B2")
    features = resp.json()["features"]
    assert "zone_avg_wait_time" in features
    assert "zone_surge_factor" in features
    assert "zone_completed_trips" in features
    assert "zone_avg_trip_distance" in features
    assert "zone_cancellation_rate" in features


@pytest.mark.anyio
async def test_timeseries(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_A1/timeseries")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_id"] == "zone_A1"
    assert data["total"] == 24  # 24 hours


@pytest.mark.anyio
async def test_timeseries_with_time_filter(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_A1/timeseries", params={
        "start_hour": "2026-03-09T08:00:00Z",
        "end_hour": "2026-03-09T12:00:00Z",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5  # hours 8, 9, 10, 11, 12


@pytest.mark.anyio
async def test_timeseries_not_found(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_ZZ/timeseries")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_timeseries_start_filter_only(client: AsyncClient):
    resp = await client.get("/pipeline/zone/features/zone_A1/timeseries", params={
        "start_hour": "2026-03-09T20:00:00Z",
    })
    assert resp.status_code == 200
    assert resp.json()["total"] == 4  # hours 20, 21, 22, 23


@pytest.mark.anyio
async def test_run_pipeline(client: AsyncClient):
    resp = await client.post("/pipeline/zone/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["features_computed"] > 0


@pytest.mark.anyio
async def test_run_pipeline_specific_zones(client: AsyncClient):
    resp = await client.post("/pipeline/zone/run", json={"zone_ids": ["zone_A1", "zone_B2"]})
    assert resp.status_code == 200
    assert resp.json()["features_computed"] == 16  # 2 zones * 8 features


@pytest.mark.anyio
async def test_run_pipeline_no_body(client: AsyncClient):
    resp = await client.post("/pipeline/zone/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.anyio
async def test_catalog(client: AsyncClient):
    resp = await client.get("/pipeline/zone/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    names = [f["name"] for f in data["features"]]
    assert "zone_demand_last_hour" in names
    assert "zone_surge_factor" in names
    assert "zone_cancellation_rate" in names


@pytest.mark.anyio
async def test_catalog_entries_have_fields(client: AsyncClient):
    resp = await client.get("/pipeline/zone/catalog")
    for entry in resp.json()["features"]:
        assert "name" in entry
        assert "description" in entry
        assert "value_type" in entry
        assert "source" in entry


@pytest.mark.anyio
async def test_twenty_zones_seeded(client: AsyncClient):
    """Verify all 20 zones are seeded by checking a few."""
    for zone_id in ["zone_A1", "zone_A5", "zone_B1", "zone_D5"]:
        resp = await client.get(f"/pipeline/zone/features/{zone_id}")
        assert resp.status_code == 200
