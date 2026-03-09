"""
Tests for ETL Worker Postgres-to-ClickHouse service.

Covers sync operations, status tracking, watermark management,
and full resync functionality.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ETL Worker" in data["service"]


@pytest.mark.anyio
async def test_sync_table_incremental(client: AsyncClient):
    response = await client.post("/sync/users", json={"mode": "incremental", "batch_size": 5000})
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "users"
    assert data["mode"] == "incremental"
    assert data["state"] == "completed"
    assert data["rows_synced"] > 0
    assert data["job_id"] is not None


@pytest.mark.anyio
async def test_sync_table_full_mode(client: AsyncClient):
    response = await client.post("/sync/drivers", json={"mode": "full"})
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "drivers"
    assert data["mode"] == "full"
    assert data["state"] == "completed"


@pytest.mark.anyio
async def test_sync_table_default_mode(client: AsyncClient):
    response = await client.post("/sync/vehicles")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "incremental"


@pytest.mark.anyio
async def test_sync_new_table(client: AsyncClient):
    response = await client.post("/sync/custom_metrics", json={"mode": "incremental"})
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "custom_metrics"
    assert data["state"] == "completed"


@pytest.mark.anyio
async def test_sync_status(client: AsyncClient):
    # Create some sync jobs first
    await client.post("/sync/users")
    await client.post("/sync/drivers")

    response = await client.get("/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "running_jobs" in data
    assert "completed_jobs" in data
    assert "failed_jobs" in data
    assert "jobs" in data
    assert data["total_jobs"] >= 2


@pytest.mark.anyio
async def test_sync_status_job_details(client: AsyncClient):
    await client.post("/sync/payments")
    response = await client.get("/sync/status")
    data = response.json()
    jobs = data["jobs"]
    assert len(jobs) >= 1
    job = next(j for j in jobs if j["table_name"] == "payments")
    assert "job_id" in job
    assert "started_at" in job


@pytest.mark.anyio
async def test_list_syncable_tables(client: AsyncClient):
    response = await client.get("/sync/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert "total" in data
    assert data["total"] >= 8  # Default tables
    table_names = [t["table_name"] for t in data["tables"]]
    assert "users" in table_names
    assert "rides" in table_names


@pytest.mark.anyio
async def test_table_watermark_after_sync(client: AsyncClient):
    await client.post("/sync/locations")
    response = await client.get("/sync/tables")
    data = response.json()
    locations = next(t for t in data["tables"] if t["table_name"] == "locations")
    assert locations["rows_synced"] > 0
    assert locations["last_sync_at"] is not None


@pytest.mark.anyio
async def test_full_resync(client: AsyncClient):
    response = await client.post("/sync/full", json={"table_name": "users", "batch_size": 10000})
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "users"
    assert data["mode"] == "full"
    assert data["state"] == "completed"
    assert data["rows_synced"] > 0


@pytest.mark.anyio
async def test_full_resync_unknown_table(client: AsyncClient):
    response = await client.post("/sync/full", json={"table_name": "nonexistent_table"})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_sync_batch_size_validation(client: AsyncClient):
    response = await client.post("/sync/users", json={"batch_size": 50})
    assert response.status_code == 422  # Below minimum


@pytest.mark.anyio
async def test_sync_job_has_timestamps(client: AsyncClient):
    response = await client.post("/sync/rides")
    assert response.status_code == 200
    data = response.json()
    assert data["started_at"] is not None
    assert data["completed_at"] is not None
