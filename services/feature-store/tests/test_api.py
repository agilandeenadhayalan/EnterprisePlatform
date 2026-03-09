"""
Tests for the Feature Store service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_definitions(client: AsyncClient):
    resp = await client.get("/features/definitions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15
    assert len(data["definitions"]) == 15


@pytest.mark.anyio
async def test_list_definitions_filter_entity_type(client: AsyncClient):
    resp = await client.get("/features/definitions", params={"entity_type": "driver"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for d in data["definitions"]:
        assert d["entity_type"] == "driver"


@pytest.mark.anyio
async def test_list_definitions_filter_zone(client: AsyncClient):
    resp = await client.get("/features/definitions", params={"entity_type": "zone"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_list_definitions_filter_location(client: AsyncClient):
    resp = await client.get("/features/definitions", params={"entity_type": "location"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_get_definition(client: AsyncClient):
    resp = await client.get("/features/definitions/driver_avg_rating")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "driver_avg_rating"
    assert data["entity_type"] == "driver"
    assert data["value_type"] == "float"


@pytest.mark.anyio
async def test_get_definition_not_found(client: AsyncClient):
    resp = await client.get("/features/definitions/nonexistent_feature")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_definition(client: AsyncClient):
    payload = {
        "name": "rider_lifetime_value",
        "entity_type": "rider",
        "value_type": "float",
        "source": "payments-db",
        "description": "Lifetime value of rider",
        "freshness_sla_seconds": 7200,
    }
    resp = await client.post("/features/definitions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "rider_lifetime_value"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_definition_duplicate(client: AsyncClient):
    payload = {
        "name": "driver_avg_rating",
        "entity_type": "driver",
        "value_type": "float",
        "source": "rides-db",
        "description": "Duplicate",
        "freshness_sla_seconds": 3600,
    }
    resp = await client.post("/features/definitions", json=payload)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_online_features_driver(client: AsyncClient):
    payload = {
        "entity_id": "driver_001",
        "feature_names": ["driver_avg_rating", "driver_total_trips_30d"],
    }
    resp = await client.post("/features/online", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "driver_001"
    assert "driver_avg_rating" in data["features"]
    assert data["features"]["driver_avg_rating"] == 4.85


@pytest.mark.anyio
async def test_online_features_zone(client: AsyncClient):
    payload = {
        "entity_id": "zone_A1",
        "feature_names": ["zone_demand_last_hour", "zone_surge_factor"],
    }
    resp = await client.post("/features/online", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["features"]["zone_demand_last_hour"] == 47.0
    assert data["features"]["zone_surge_factor"] == 1.4


@pytest.mark.anyio
async def test_online_features_missing(client: AsyncClient):
    payload = {
        "entity_id": "driver_999",
        "feature_names": ["driver_avg_rating"],
    }
    resp = await client.post("/features/online", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["features"] == {}


@pytest.mark.anyio
async def test_offline_features(client: AsyncClient):
    payload = {
        "entity_ids": ["driver_001", "driver_002"],
        "feature_names": ["driver_avg_rating", "driver_total_trips_30d"],
    }
    resp = await client.post("/features/offline", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["vectors"]) == 2
    assert data["vectors"][0]["entity_id"] == "driver_001"
    assert data["vectors"][1]["entity_id"] == "driver_002"


@pytest.mark.anyio
async def test_offline_features_with_missing(client: AsyncClient):
    payload = {
        "entity_ids": ["driver_001", "driver_999"],
        "feature_names": ["driver_avg_rating"],
    }
    resp = await client.post("/features/offline", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["vectors"][1]["features"] == {}


@pytest.mark.anyio
async def test_ingest_feature(client: AsyncClient):
    payload = {
        "entity_id": "driver_003",
        "feature_name": "driver_avg_rating",
        "value": 4.55,
        "timestamp": "2026-03-09T14:00:00Z",
    }
    resp = await client.post("/features/ingest", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1

    # Verify it's retrievable
    online = await client.post("/features/online", json={
        "entity_id": "driver_003",
        "feature_names": ["driver_avg_rating"],
    })
    assert online.json()["features"]["driver_avg_rating"] == 4.55


@pytest.mark.anyio
async def test_ingest_without_timestamp(client: AsyncClient):
    payload = {
        "entity_id": "driver_004",
        "feature_name": "driver_cancel_rate",
        "value": 0.05,
    }
    resp = await client.post("/features/ingest", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/features/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_definitions"] == 15
    assert data["active_definitions"] == 15
    assert data["total_values"] == 18
    assert "driver" in data["entity_types"]
    assert "zone" in data["entity_types"]
    assert "location" in data["entity_types"]


@pytest.mark.anyio
async def test_stats_after_ingest(client: AsyncClient):
    payload = {
        "entity_id": "driver_010",
        "feature_name": "driver_avg_rating",
        "value": 4.0,
    }
    await client.post("/features/ingest", json=payload)
    resp = await client.get("/features/stats")
    assert resp.json()["total_values"] == 19


@pytest.mark.anyio
async def test_create_then_list(client: AsyncClient):
    payload = {
        "name": "rider_trip_count",
        "entity_type": "rider",
        "value_type": "int",
        "source": "rides-db",
        "description": "Total trips by rider",
        "freshness_sla_seconds": 3600,
    }
    await client.post("/features/definitions", json=payload)
    resp = await client.get("/features/definitions")
    assert resp.json()["total"] == 16
