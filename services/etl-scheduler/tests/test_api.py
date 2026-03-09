"""
Tests for ETL Scheduler service.

Covers full CRUD operations, job triggering, execution history,
scheduling validation, and job state management.
"""

import pytest
from httpx import AsyncClient


SAMPLE_JOB = {
    "name": "Sync Users Table",
    "description": "Hourly sync of users from Postgres to ClickHouse",
    "cron_expression": "0 * * * *",
    "config": {
        "target_service": "etl-worker-postgres-to-ch",
        "target_endpoint": "/sync/users",
        "payload": {"mode": "incremental"},
        "timeout_seconds": 3600,
        "retry_count": 3,
        "retry_delay_seconds": 60,
    },
    "enabled": True,
}


async def create_sample_job(client: AsyncClient) -> dict:
    response = await client.post("/jobs", json=SAMPLE_JOB)
    return response.json()


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Scheduler" in data["service"]


@pytest.mark.anyio
async def test_create_job(client: AsyncClient):
    response = await client.post("/jobs", json=SAMPLE_JOB)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sync Users Table"
    assert data["state"] == "idle"
    assert data["enabled"] is True
    assert data["job_id"] is not None
    assert data["cron_schedule"]["expression"] == "0 * * * *"
    assert data["config"]["target_service"] == "etl-worker-postgres-to-ch"


@pytest.mark.anyio
async def test_create_job_invalid_cron(client: AsyncClient):
    job_data = {**SAMPLE_JOB, "cron_expression": "invalid"}
    response = await client.post("/jobs", json=job_data)
    assert response.status_code == 400


@pytest.mark.anyio
async def test_list_jobs(client: AsyncClient):
    await create_sample_job(client)
    await create_sample_job(client)

    response = await client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert data["total"] >= 2


@pytest.mark.anyio
async def test_get_job(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["name"] == "Sync Users Table"


@pytest.mark.anyio
async def test_get_job_not_found(client: AsyncClient):
    response = await client.get("/jobs/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_job_name(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.patch(f"/jobs/{job_id}", json={"name": "Updated Job Name"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Job Name"


@pytest.mark.anyio
async def test_update_job_schedule(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.patch(f"/jobs/{job_id}", json={"cron_expression": "30 2 * * *"})
    assert response.status_code == 200
    data = response.json()
    assert data["cron_schedule"]["expression"] == "30 2 * * *"
    assert data["cron_schedule"]["minute"] == "30"
    assert data["cron_schedule"]["hour"] == "2"


@pytest.mark.anyio
async def test_update_job_disable(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.patch(f"/jobs/{job_id}", json={"enabled": False})
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["state"] == "disabled"


@pytest.mark.anyio
async def test_update_job_not_found(client: AsyncClient):
    response = await client.patch("/jobs/nonexistent-id", json={"name": "Test"})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_job(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.delete(f"/jobs/{job_id}")
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_job_not_found(client: AsyncClient):
    response = await client.delete("/jobs/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_trigger_job(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    response = await client.post(f"/jobs/{job_id}/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["execution_id"] is not None
    assert data["message"] == "Job triggered successfully"
    assert data["state"] == "completed"


@pytest.mark.anyio
async def test_trigger_job_not_found(client: AsyncClient):
    response = await client.post("/jobs/nonexistent-id/trigger")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_job_history(client: AsyncClient):
    created = await create_sample_job(client)
    job_id = created["job_id"]

    # Trigger the job twice
    await client.post(f"/jobs/{job_id}/trigger")
    await client.post(f"/jobs/{job_id}/trigger")

    response = await client.get(f"/jobs/{job_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert "executions" in data
    assert "total" in data
    assert data["total"] >= 2
    for execution in data["executions"]:
        assert execution["job_id"] == job_id
        assert "execution_id" in execution
        assert "started_at" in execution


@pytest.mark.anyio
async def test_job_history_not_found(client: AsyncClient):
    response = await client.get("/jobs/nonexistent-id/history")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_job_has_next_run(client: AsyncClient):
    created = await create_sample_job(client)
    assert created["next_run_at"] is not None
