"""
Tests for the ML Training Service API.

Covers: job submission, listing, status filtering, metrics, cancellation,
architecture listing, logs, edge cases.
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
async def test_list_training_jobs(client: AsyncClient):
    """List all training jobs returns seeded data."""
    resp = await client.get("/training/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["jobs"]) == 5


@pytest.mark.anyio
async def test_list_training_jobs_filter_completed(client: AsyncClient):
    """Filter training jobs by completed status."""
    resp = await client.get("/training/jobs?status=completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for job in data["jobs"]:
        assert job["status"] == "completed"


@pytest.mark.anyio
async def test_list_training_jobs_filter_running(client: AsyncClient):
    """Filter training jobs by running status."""
    resp = await client.get("/training/jobs?status=running")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["status"] == "running"


@pytest.mark.anyio
async def test_list_training_jobs_filter_pending(client: AsyncClient):
    """Filter by pending status returns empty when none pending."""
    resp = await client.get("/training/jobs?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.anyio
async def test_get_training_job(client: AsyncClient):
    """Get a specific training job by ID."""
    resp = await client.get("/training/jobs/job-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "job-001"
    assert data["model_type"] == "fare_predictor_rf"
    assert data["status"] == "completed"
    assert data["dataset_id"] == "fare_training_v1"


@pytest.mark.anyio
async def test_get_training_job_has_metrics(client: AsyncClient):
    """Completed job has epoch-by-epoch metrics."""
    resp = await client.get("/training/jobs/job-002")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["metrics"]) == 10
    first = data["metrics"][0]
    assert first["epoch"] == 1
    assert "train_loss" in first
    assert "val_loss" in first
    assert "train_metric" in first
    assert "val_metric" in first


@pytest.mark.anyio
async def test_get_training_job_metrics_decrease(client: AsyncClient):
    """Training loss should decrease over epochs."""
    resp = await client.get("/training/jobs/job-002")
    data = resp.json()
    metrics = data["metrics"]
    for i in range(len(metrics) - 1):
        assert metrics[i]["train_loss"] > metrics[i + 1]["train_loss"]


@pytest.mark.anyio
async def test_get_training_job_not_found(client: AsyncClient):
    """Requesting a nonexistent job returns 404."""
    resp = await client.get("/training/jobs/job-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_submit_training_job(client: AsyncClient):
    """Submit a new training job."""
    body = {
        "model_type": "fare_predictor_rf",
        "hyperparameters": {"n_estimators": 200},
        "dataset_id": "fare_training_v1",
    }
    resp = await client.post("/training/jobs", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_type"] == "fare_predictor_rf"
    assert data["status"] == "pending"
    assert data["dataset_id"] == "fare_training_v1"
    assert data["hyperparameters"]["n_estimators"] == 200


@pytest.mark.anyio
async def test_submit_training_job_appears_in_list(client: AsyncClient):
    """Newly submitted job appears in the job list."""
    body = {
        "model_type": "demand_predictor_gb",
        "hyperparameters": {},
        "dataset_id": "demand_training_v1",
    }
    await client.post("/training/jobs", json=body)
    resp = await client.get("/training/jobs")
    assert resp.json()["total"] == 6


@pytest.mark.anyio
async def test_submit_training_job_default_hyperparams(client: AsyncClient):
    """Submit job with empty hyperparameters."""
    body = {
        "model_type": "eta_predictor_nn",
        "hyperparameters": {},
        "dataset_id": "eta_training_v1",
    }
    resp = await client.post("/training/jobs", json=body)
    assert resp.status_code == 201
    assert resp.json()["hyperparameters"] == {}


@pytest.mark.anyio
async def test_cancel_running_job(client: AsyncClient):
    """Cancel a running job changes status to cancelled."""
    resp = await client.post("/training/jobs/job-005/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"


@pytest.mark.anyio
async def test_cancel_completed_job_no_change(client: AsyncClient):
    """Cancelling a completed job does not change its status."""
    resp = await client.post("/training/jobs/job-001/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_cancel_nonexistent_job(client: AsyncClient):
    """Cancelling a nonexistent job returns 404."""
    resp = await client.post("/training/jobs/job-nonexistent/cancel")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_model_architectures(client: AsyncClient):
    """List all model architectures."""
    resp = await client.get("/training/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    names = [a["name"] for a in data["architectures"]]
    assert "fare_predictor_rf" in names
    assert "fare_predictor_nn" in names
    assert "demand_predictor_gb" in names
    assert "eta_predictor_nn" in names


@pytest.mark.anyio
async def test_model_architecture_has_defaults(client: AsyncClient):
    """Each architecture has default hyperparameters."""
    resp = await client.get("/training/models")
    data = resp.json()
    for arch in data["architectures"]:
        assert "default_hyperparameters" in arch
        assert isinstance(arch["default_hyperparameters"], dict)
        assert len(arch["default_hyperparameters"]) > 0


@pytest.mark.anyio
async def test_get_training_logs(client: AsyncClient):
    """Get training logs for a job."""
    resp = await client.get("/training/jobs/job-001/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == "job-001"
    assert data["total"] > 0
    assert len(data["logs"]) > 0


@pytest.mark.anyio
async def test_get_training_logs_not_found(client: AsyncClient):
    """Requesting logs for nonexistent job returns 404."""
    resp = await client.get("/training/jobs/job-nonexistent/logs")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_job_has_timestamps(client: AsyncClient):
    """Completed jobs have started_at and completed_at timestamps."""
    resp = await client.get("/training/jobs/job-001")
    data = resp.json()
    assert data["created_at"] is not None
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


@pytest.mark.anyio
async def test_running_job_no_completed_at(client: AsyncClient):
    """Running job has no completed_at timestamp."""
    resp = await client.get("/training/jobs/job-005")
    data = resp.json()
    assert data["status"] == "running"
    assert data["started_at"] is not None
    assert data["completed_at"] is None
