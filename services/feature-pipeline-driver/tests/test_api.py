"""
Tests for the Feature Pipeline Driver service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_get_driver_features(client: AsyncClient):
    resp = await client.get("/pipeline/driver/features/driver_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["driver_id"] == "driver_001"
    assert "driver_avg_rating" in data["features"]
    assert "driver_total_trips_30d" in data["features"]
    assert "driver_earnings_per_hour" in data["features"]


@pytest.mark.anyio
async def test_get_driver_features_not_found(client: AsyncClient):
    resp = await client.get("/pipeline/driver/features/driver_999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_driver_features_has_all_catalog_features(client: AsyncClient):
    resp = await client.get("/pipeline/driver/features/driver_005")
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert "driver_acceptance_rate" in features
    assert "driver_cancel_rate" in features
    assert "driver_online_hours_7d" in features
    assert "driver_peak_hour_pct" in features
    assert "driver_avg_trip_distance" in features


@pytest.mark.anyio
async def test_pipeline_status(client: AsyncClient):
    resp = await client.get("/pipeline/driver/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 3
    assert data["last_run_status"] == "completed"
    assert len(data["runs"]) == 3


@pytest.mark.anyio
async def test_pipeline_status_run_details(client: AsyncClient):
    resp = await client.get("/pipeline/driver/status")
    data = resp.json()
    first_run = data["runs"][0]
    assert first_run["id"] == "run_001"
    assert first_run["status"] == "completed"
    assert first_run["features_computed"] == 120


@pytest.mark.anyio
async def test_run_pipeline_all_drivers(client: AsyncClient):
    resp = await client.post("/pipeline/driver/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["features_computed"] > 0


@pytest.mark.anyio
async def test_run_pipeline_specific_drivers(client: AsyncClient):
    resp = await client.post("/pipeline/driver/run", json={"driver_ids": ["driver_001", "driver_002"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["features_computed"] == 16  # 2 drivers * 8 features


@pytest.mark.anyio
async def test_run_pipeline_new_driver(client: AsyncClient):
    resp = await client.post("/pipeline/driver/run", json={"driver_ids": ["driver_new_01"]})
    assert resp.status_code == 200

    features_resp = await client.get("/pipeline/driver/features/driver_new_01")
    assert features_resp.status_code == 200
    assert features_resp.json()["driver_id"] == "driver_new_01"


@pytest.mark.anyio
async def test_run_pipeline_adds_to_status(client: AsyncClient):
    await client.post("/pipeline/driver/run", json={})
    resp = await client.get("/pipeline/driver/status")
    assert resp.json()["total_runs"] == 4


@pytest.mark.anyio
async def test_catalog(client: AsyncClient):
    resp = await client.get("/pipeline/driver/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    names = [f["name"] for f in data["features"]]
    assert "driver_avg_rating" in names
    assert "driver_total_trips_30d" in names


@pytest.mark.anyio
async def test_catalog_entries_have_fields(client: AsyncClient):
    resp = await client.get("/pipeline/driver/catalog")
    entry = resp.json()["features"][0]
    assert "name" in entry
    assert "description" in entry
    assert "value_type" in entry
    assert "source" in entry


@pytest.mark.anyio
async def test_seeded_drivers_count(client: AsyncClient):
    resp = await client.get("/pipeline/driver/status")
    assert resp.status_code == 200
    # We have 15 drivers seeded, verify by fetching driver_015
    features_resp = await client.get("/pipeline/driver/features/driver_015")
    assert features_resp.status_code == 200


@pytest.mark.anyio
async def test_feature_values_in_range(client: AsyncClient):
    resp = await client.get("/pipeline/driver/features/driver_001")
    features = resp.json()["features"]
    assert 3.0 <= features["driver_avg_rating"] <= 5.0
    assert 0.0 <= features["driver_acceptance_rate"] <= 1.0
    assert 0.0 <= features["driver_cancel_rate"] <= 1.0


@pytest.mark.anyio
async def test_run_pipeline_no_body(client: AsyncClient):
    resp = await client.post("/pipeline/driver/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.anyio
async def test_multiple_pipeline_runs(client: AsyncClient):
    await client.post("/pipeline/driver/run", json={})
    await client.post("/pipeline/driver/run", json={})
    resp = await client.get("/pipeline/driver/status")
    assert resp.json()["total_runs"] == 5
