"""
Tests for the Batch Prediction Service API.

Covers: job submission, listing, progress tracking, result pagination,
cancellation, filtering, and error handling.
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
async def test_list_jobs(client: AsyncClient):
    """List all batch jobs returns seeded jobs."""
    resp = await client.get("/batch/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_list_jobs_filter_by_status(client: AsyncClient):
    """List jobs filtered by status."""
    resp = await client.get("/batch/jobs?status=completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["status"] == "completed"


@pytest.mark.anyio
async def test_list_jobs_filter_running(client: AsyncClient):
    """List jobs filtered by running status."""
    resp = await client.get("/batch/jobs?status=running")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["status"] == "running"


@pytest.mark.anyio
async def test_get_job_details(client: AsyncClient):
    """Get details for a specific batch job."""
    resp = await client.get("/batch/jobs/batch-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "batch-001"
    assert data["model_name"] == "fare_predictor"
    assert data["status"] == "completed"
    assert data["total_records"] == 500
    assert data["processed_records"] == 500


@pytest.mark.anyio
async def test_get_job_running_progress(client: AsyncClient):
    """Running job shows partial progress."""
    resp = await client.get("/batch/jobs/batch-002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["processed_records"] < data["total_records"]
    assert data["processed_records"] == 120


@pytest.mark.anyio
async def test_get_job_not_found(client: AsyncClient):
    """Getting a non-existent job returns 404."""
    resp = await client.get("/batch/jobs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_job(client: AsyncClient):
    """Submit a new batch prediction job."""
    resp = await client.post("/batch/jobs", json={
        "model_name": "fare_predictor",
        "dataset_id": "ds-test-001",
        "output_format": "json",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_name"] == "fare_predictor"
    assert data["dataset_id"] == "ds-test-001"
    assert data["status"] == "pending"
    assert data["processed_records"] == 0
    assert data["total_records"] > 0


@pytest.mark.anyio
async def test_create_job_appears_in_list(client: AsyncClient):
    """Newly created job appears in the job list."""
    await client.post("/batch/jobs", json={
        "model_name": "eta_predictor",
        "dataset_id": "ds-test-002",
    })
    resp = await client.get("/batch/jobs")
    assert resp.json()["total"] == 4


@pytest.mark.anyio
async def test_get_results_completed_job(client: AsyncClient):
    """Get results for a completed job returns predictions."""
    resp = await client.get("/batch/jobs/batch-001/results?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 500
    assert len(data["results"]) == 10
    assert data["page"] == 1
    assert data["page_size"] == 10
    result = data["results"][0]
    assert "entity_id" in result
    assert "prediction" in result
    assert "confidence" in result


@pytest.mark.anyio
async def test_get_results_pagination(client: AsyncClient):
    """Results pagination returns different pages."""
    page1 = await client.get("/batch/jobs/batch-001/results?page=1&page_size=20")
    page2 = await client.get("/batch/jobs/batch-001/results?page=2&page_size=20")
    assert page1.status_code == 200
    assert page2.status_code == 200
    ids1 = [r["entity_id"] for r in page1.json()["results"]]
    ids2 = [r["entity_id"] for r in page2.json()["results"]]
    assert len(set(ids1) & set(ids2)) == 0  # No overlap


@pytest.mark.anyio
async def test_get_results_empty_job(client: AsyncClient):
    """Results for a job with no results returns empty list."""
    resp = await client.get("/batch/jobs/batch-003/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []


@pytest.mark.anyio
async def test_get_results_not_found(client: AsyncClient):
    """Results for non-existent job returns 404."""
    resp = await client.get("/batch/jobs/nonexistent/results")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_cancel_pending_job(client: AsyncClient):
    """Cancel a pending job sets status to cancelled."""
    resp = await client.post("/batch/jobs/batch-003/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.anyio
async def test_cancel_running_job(client: AsyncClient):
    """Cancel a running job sets status to cancelled."""
    resp = await client.post("/batch/jobs/batch-002/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.anyio
async def test_cancel_completed_job_no_effect(client: AsyncClient):
    """Cancelling a completed job has no effect on status."""
    resp = await client.post("/batch/jobs/batch-001/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
