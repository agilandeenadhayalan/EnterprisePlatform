"""
Tests for the Data Replication Service API.

Covers: job creation, listing, status, cancellation, and validation.
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
async def test_start_replication_ch_to_minio(client: AsyncClient):
    """Start a ClickHouse to MinIO replication job."""
    resp = await client.post("/replicate", json={
        "direction": "ch_to_minio",
        "source": "mobility_analytics.ride_events",
        "destination": "bronze/ride-events/",
        "format": "parquet",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["direction"] == "ch_to_minio"
    assert data["source"] == "mobility_analytics.ride_events"
    assert data["status"] == "completed"
    assert data["records_processed"] > 0
    assert "id" in data


@pytest.mark.anyio
async def test_start_replication_minio_to_ch(client: AsyncClient):
    """Start a MinIO to ClickHouse replication job."""
    resp = await client.post("/replicate", json={
        "direction": "minio_to_ch",
        "source": "silver/clean-rides/",
        "destination": "mobility_analytics.clean_rides",
    })
    assert resp.status_code == 201
    assert resp.json()["direction"] == "minio_to_ch"


@pytest.mark.anyio
async def test_start_replication_invalid_direction(client: AsyncClient):
    """Invalid replication direction returns 400."""
    resp = await client.post("/replicate", json={
        "direction": "invalid",
        "source": "src",
        "destination": "dst",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_jobs_empty(client: AsyncClient):
    """List jobs when none exist."""
    resp = await client.get("/replicate/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["jobs"] == []


@pytest.mark.anyio
async def test_list_jobs(client: AsyncClient):
    """List all replication jobs."""
    await client.post("/replicate", json={
        "direction": "ch_to_minio", "source": "t1", "destination": "b1",
    })
    await client.post("/replicate", json={
        "direction": "minio_to_ch", "source": "b2", "destination": "t2",
    })

    resp = await client.get("/replicate/jobs")
    assert resp.json()["total"] == 2


@pytest.mark.anyio
async def test_get_job(client: AsyncClient):
    """Get a specific job by ID."""
    create_resp = await client.post("/replicate", json={
        "direction": "ch_to_minio", "source": "table1", "destination": "bucket1/",
    })
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/replicate/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id
    assert resp.json()["source"] == "table1"


@pytest.mark.anyio
async def test_get_job_not_found(client: AsyncClient):
    """Getting a non-existent job returns 404."""
    resp = await client.get("/replicate/jobs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_cancel_job(client: AsyncClient):
    """Cancel a replication job."""
    create_resp = await client.post("/replicate", json={
        "direction": "ch_to_minio", "source": "t1", "destination": "b1",
    })
    job_id = create_resp.json()["id"]

    resp = await client.post(f"/replicate/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    # Job was already completed, so status stays completed
    assert resp.json()["status"] in ("completed", "cancelled")


@pytest.mark.anyio
async def test_cancel_job_not_found(client: AsyncClient):
    """Cancelling non-existent job returns 404."""
    resp = await client.post("/replicate/jobs/nonexistent/cancel")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_replication_has_bytes_transferred(client: AsyncClient):
    """Replication job tracks bytes transferred."""
    resp = await client.post("/replicate", json={
        "direction": "ch_to_minio", "source": "table", "destination": "bucket/",
    })
    data = resp.json()
    assert data["bytes_transferred"] > 0
    assert data["records_total"] > 0
    assert data["records_processed"] == data["records_total"]
