"""
Tests for the Data Catalog Service API.

Covers: CRUD operations, search, filtering, stats, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_DATASET = {
    "name": "ride_events",
    "description": "All ride start/end events from the ride service",
    "store": "clickhouse",
    "location": "mobility_analytics.ride_events",
    "schema_fields": [
        {"name": "ride_id", "type": "String"},
        {"name": "started_at", "type": "DateTime"},
    ],
    "format": "native",
    "owner": "data-team",
    "tags": ["rides", "events", "real-time"],
    "size_bytes": 1048576,
    "record_count": 50000,
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_dataset(client: AsyncClient):
    """Register a new dataset in the catalog."""
    resp = await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ride_events"
    assert data["store"] == "clickhouse"
    assert "id" in data
    assert len(data["schema_fields"]) == 2


@pytest.mark.anyio
async def test_get_dataset(client: AsyncClient):
    """Retrieve a specific dataset by ID."""
    create_resp = await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    dataset_id = create_resp.json()["id"]

    resp = await client.get(f"/catalog/datasets/{dataset_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == dataset_id
    assert resp.json()["name"] == "ride_events"


@pytest.mark.anyio
async def test_get_dataset_not_found(client: AsyncClient):
    """Getting a non-existent dataset returns 404."""
    resp = await client.get("/catalog/datasets/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_datasets_empty(client: AsyncClient):
    """Listing datasets when none exist returns empty list."""
    resp = await client.get("/catalog/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["datasets"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_list_datasets(client: AsyncClient):
    """List all registered datasets."""
    await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    await client.post("/catalog/datasets", json={
        **SAMPLE_DATASET,
        "name": "driver_locations",
        "store": "minio",
        "location": "bronze/driver-locations/",
    })

    resp = await client.get("/catalog/datasets")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.anyio
async def test_list_datasets_filter_by_store(client: AsyncClient):
    """Filter datasets by storage backend."""
    await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    await client.post("/catalog/datasets", json={
        **SAMPLE_DATASET, "name": "gps_data", "store": "minio",
    })

    resp = await client.get("/catalog/datasets?store=clickhouse")
    assert resp.json()["total"] == 1
    assert resp.json()["datasets"][0]["store"] == "clickhouse"


@pytest.mark.anyio
async def test_list_datasets_search(client: AsyncClient):
    """Search datasets by keyword in name/description/tags."""
    await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    await client.post("/catalog/datasets", json={
        **SAMPLE_DATASET,
        "name": "weather_data",
        "description": "Weather observations",
        "tags": ["weather"],
    })

    resp = await client.get("/catalog/datasets?q=ride")
    assert resp.json()["total"] == 1
    assert resp.json()["datasets"][0]["name"] == "ride_events"


@pytest.mark.anyio
async def test_update_dataset(client: AsyncClient):
    """Update dataset metadata with PATCH."""
    create_resp = await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    dataset_id = create_resp.json()["id"]

    resp = await client.patch(f"/catalog/datasets/{dataset_id}", json={
        "description": "Updated description",
        "record_count": 75000,
    })
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"
    assert resp.json()["record_count"] == 75000
    assert resp.json()["name"] == "ride_events"  # unchanged


@pytest.mark.anyio
async def test_update_dataset_not_found(client: AsyncClient):
    """Updating a non-existent dataset returns 404."""
    resp = await client.patch("/catalog/datasets/nonexistent", json={"name": "x"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_dataset(client: AsyncClient):
    """Remove a dataset from the catalog."""
    create_resp = await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    dataset_id = create_resp.json()["id"]

    resp = await client.delete(f"/catalog/datasets/{dataset_id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/catalog/datasets/{dataset_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_dataset_not_found(client: AsyncClient):
    """Deleting a non-existent dataset returns 404."""
    resp = await client.delete("/catalog/datasets/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_search_datasets(client: AsyncClient):
    """Dedicated search endpoint finds datasets by keyword."""
    await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    await client.post("/catalog/datasets", json={
        **SAMPLE_DATASET, "name": "payment_records", "tags": ["payments"],
    })

    resp = await client.get("/catalog/search?q=events")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_catalog_stats(client: AsyncClient):
    """Get catalog statistics — count per store, total size."""
    await client.post("/catalog/datasets", json=SAMPLE_DATASET)
    await client.post("/catalog/datasets", json={
        **SAMPLE_DATASET,
        "name": "gps",
        "store": "minio",
        "size_bytes": 2097152,
        "record_count": 100000,
    })

    resp = await client.get("/catalog/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_datasets"] == 2
    assert data["by_store"]["clickhouse"] == 1
    assert data["by_store"]["minio"] == 1
    assert data["total_size_bytes"] == 1048576 + 2097152
    assert data["total_records"] == 50000 + 100000


@pytest.mark.anyio
async def test_catalog_stats_empty(client: AsyncClient):
    """Stats on empty catalog returns zeros."""
    resp = await client.get("/catalog/stats")
    data = resp.json()
    assert data["total_datasets"] == 0
    assert data["by_store"] == {}
    assert data["total_size_bytes"] == 0
