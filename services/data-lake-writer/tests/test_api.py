"""
Tests for the Data Lake Writer API.

Covers: writing to layers, layer stats, bronze-to-silver transforms,
silver-to-gold transforms, validation, and edge cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_write_to_bronze(client: AsyncClient):
    """Write raw data to the bronze layer."""
    resp = await client.post("/write/bronze", json={
        "source": "gps-tracker",
        "data": {"lat": 40.7128, "lng": -74.0060, "speed": 35.5},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["layer"] == "bronze"
    assert data["source"] == "gps-tracker"
    assert "record_id" in data
    assert data["message"] == "Record written successfully"


@pytest.mark.anyio
async def test_write_to_silver(client: AsyncClient):
    """Write cleaned data to the silver layer."""
    resp = await client.post("/write/silver", json={
        "source": "ride-service",
        "data": {"ride_id": "r-123", "status": "completed"},
    })
    assert resp.status_code == 201
    assert resp.json()["layer"] == "silver"


@pytest.mark.anyio
async def test_write_to_gold(client: AsyncClient):
    """Write aggregated data to the gold layer."""
    resp = await client.post("/write/gold", json={
        "source": "analytics",
        "data": {"metric": "daily_rides", "value": 1500},
    })
    assert resp.status_code == 201
    assert resp.json()["layer"] == "gold"


@pytest.mark.anyio
async def test_write_with_metadata(client: AsyncClient):
    """Write data with optional metadata."""
    resp = await client.post("/write/bronze", json={
        "source": "gps-tracker",
        "data": {"lat": 40.7128},
        "metadata": {"device_id": "dev-001", "firmware": "v2.1"},
    })
    assert resp.status_code == 201


@pytest.mark.anyio
async def test_write_invalid_layer(client: AsyncClient):
    """Writing to an invalid layer returns 400."""
    resp = await client.post("/write/platinum", json={
        "source": "test",
        "data": {"key": "value"},
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_layers_empty(client: AsyncClient):
    """List layers returns all three layers with zero counts when empty."""
    resp = await client.get("/layers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["layers"]) == 3
    assert data["total_objects"] == 0
    assert data["total_size_bytes"] == 0
    layer_names = [l["layer"] for l in data["layers"]]
    assert "bronze" in layer_names
    assert "silver" in layer_names
    assert "gold" in layer_names


@pytest.mark.anyio
async def test_list_layers_with_data(client: AsyncClient):
    """List layers shows correct counts after writing data."""
    await client.post("/write/bronze", json={"source": "s1", "data": {"a": 1}})
    await client.post("/write/bronze", json={"source": "s2", "data": {"b": 2}})
    await client.post("/write/silver", json={"source": "s1", "data": {"c": 3}})

    resp = await client.get("/layers")
    data = resp.json()
    assert data["total_objects"] == 3

    bronze = next(l for l in data["layers"] if l["layer"] == "bronze")
    silver = next(l for l in data["layers"] if l["layer"] == "silver")
    assert bronze["object_count"] == 2
    assert silver["object_count"] == 1


@pytest.mark.anyio
async def test_layer_stats(client: AsyncClient):
    """Get detailed stats for a specific layer."""
    await client.post("/write/bronze", json={"source": "gps", "data": {"lat": 1.0}})
    resp = await client.get("/layers/bronze/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["layer"] == "bronze"
    assert data["object_count"] == 1
    assert data["total_size_bytes"] > 0


@pytest.mark.anyio
async def test_layer_stats_invalid_layer(client: AsyncClient):
    """Getting stats for invalid layer returns 400."""
    resp = await client.get("/layers/invalid/stats")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_transform_bronze_to_silver(client: AsyncClient):
    """Bronze-to-Silver transform cleans and deduplicates data."""
    # Write bronze records (including one with nulls and a duplicate)
    await client.post("/write/bronze", json={
        "source": "gps", "data": {"lat": 40.7, "lng": -74.0, "extra": None},
    })
    await client.post("/write/bronze", json={
        "source": "gps", "data": {"lat": 40.7, "lng": -74.0, "extra": None},
    })
    await client.post("/write/bronze", json={
        "source": "gps", "data": {"lat": 41.0, "lng": -73.5},
    })

    resp = await client.post("/transform/bronze-to-silver", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_layer"] == "bronze"
    assert data["target_layer"] == "silver"
    assert data["status"] == "completed"
    assert data["records_in"] == 3
    # Dedup: 2 identical records → 1 unique + 1 different = 2 out
    assert data["records_out"] == 2


@pytest.mark.anyio
async def test_transform_bronze_to_silver_with_source_filter(client: AsyncClient):
    """Bronze-to-Silver transform can filter by source."""
    await client.post("/write/bronze", json={"source": "gps", "data": {"lat": 1.0}})
    await client.post("/write/bronze", json={"source": "rides", "data": {"id": "r1"}})

    resp = await client.post("/transform/bronze-to-silver", json={"source_filter": "gps"})
    data = resp.json()
    assert data["records_in"] == 1
    assert data["records_out"] == 1


@pytest.mark.anyio
async def test_transform_silver_to_gold(client: AsyncClient):
    """Silver-to-Gold transform aggregates by source."""
    # Write silver records from two sources
    await client.post("/write/silver", json={"source": "gps", "data": {"lat": 1.0, "speed": 30}})
    await client.post("/write/silver", json={"source": "gps", "data": {"lat": 2.0, "speed": 45}})
    await client.post("/write/silver", json={"source": "rides", "data": {"fare": 25.50}})

    resp = await client.post("/transform/silver-to-gold", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_layer"] == "silver"
    assert data["target_layer"] == "gold"
    assert data["status"] == "completed"
    assert data["records_in"] == 3
    # Two sources → two gold records
    assert data["records_out"] == 2


@pytest.mark.anyio
async def test_transform_empty_layer(client: AsyncClient):
    """Transform on empty layer completes with zero records."""
    resp = await client.post("/transform/bronze-to-silver", json={})
    data = resp.json()
    assert data["status"] == "completed"
    assert data["records_in"] == 0
    assert data["records_out"] == 0


@pytest.mark.anyio
async def test_full_medallion_pipeline(client: AsyncClient):
    """End-to-end: Bronze → Silver → Gold pipeline."""
    # Write raw data to bronze
    for i in range(5):
        await client.post("/write/bronze", json={
            "source": "sensors",
            "data": {"reading": i * 10, "sensor_id": f"s-{i}"},
        })

    # Transform bronze → silver
    resp = await client.post("/transform/bronze-to-silver", json={})
    assert resp.json()["records_out"] == 5

    # Transform silver → gold
    resp = await client.post("/transform/silver-to-gold", json={})
    assert resp.json()["records_out"] == 1  # All from same source

    # Check final stats
    resp = await client.get("/layers")
    data = resp.json()
    bronze = next(l for l in data["layers"] if l["layer"] == "bronze")
    silver = next(l for l in data["layers"] if l["layer"] == "silver")
    gold = next(l for l in data["layers"] if l["layer"] == "gold")
    assert bronze["object_count"] == 5
    assert silver["object_count"] == 5
    assert gold["object_count"] == 1
