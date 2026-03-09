"""
Tests for the Chaos Experiment service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_experiments(client: AsyncClient):
    resp = await client.get("/chaos/experiments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["experiments"]) == 4


@pytest.mark.anyio
async def test_list_filter_type(client: AsyncClient):
    resp = await client.get("/chaos/experiments", params={"type": "latency-injection"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["experiments"][0]["experiment_type"] == "latency-injection"


@pytest.mark.anyio
async def test_list_filter_status(client: AsyncClient):
    resp = await client.get("/chaos/experiments", params={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for e in data["experiments"]:
        assert e["status"] == "completed"


@pytest.mark.anyio
async def test_create_experiment(client: AsyncClient):
    payload = {
        "name": "Memory Pressure Test",
        "experiment_type": "disk-fill",
        "target_service": "logging-service",
        "blast_radius": "single-service",
        "duration_seconds": 120,
        "parameters": {"fill_percent": 90},
    }
    resp = await client.post("/chaos/experiments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Memory Pressure Test"
    assert data["status"] == "draft"
    assert data["parameters"]["fill_percent"] == 90


@pytest.mark.anyio
async def test_get_experiment(client: AsyncClient):
    resp = await client.get("/chaos/experiments/exp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Auth Service Latency"
    assert data["experiment_type"] == "latency-injection"
    assert data["parameters"]["delay_ms"] == 200


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/chaos/experiments/exp-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_start_run(client: AsyncClient):
    # exp-004 is approved, can be run
    resp = await client.post("/chaos/experiments/exp-004/run")
    assert resp.status_code == 201
    data = resp.json()
    assert data["experiment_id"] == "exp-004"
    assert data["result"] == "pending"
    assert data["steady_state_before"]["error_rate"] > 0


@pytest.mark.anyio
async def test_start_run_draft_error(client: AsyncClient):
    # exp-003 is draft, should fail
    resp = await client.post("/chaos/experiments/exp-003/run")
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    resp = await client.get("/chaos/experiments/exp-001/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["runs"]) == 4


@pytest.mark.anyio
async def test_blast_radius(client: AsyncClient):
    resp = await client.get("/chaos/experiments/exp-001/blast-radius")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert data["target_service"] == "auth-service"
    assert "auth-service" in data["affected_services"]
    assert len(data["affected_services"]) >= 1


@pytest.mark.anyio
async def test_verify_steady_state_pass(client: AsyncClient):
    # exp-002 latest run (run-008) has good metrics: error_rate=0.006, p99=200, avail=99.95
    resp = await client.post("/chaos/experiments/exp-002/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert len(data["results"]) == 3
    for r in data["results"]:
        assert r["passed"] is True


@pytest.mark.anyio
async def test_verify_steady_state_fail(client: AsyncClient):
    # exp-001 latest run (run-004) has bad metrics: error_rate=0.020, p99=750, avail=99.80
    resp = await client.post("/chaos/experiments/exp-001/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    # At least p99_latency_ms and availability_percent should fail
    failed = [r for r in data["results"] if not r["passed"]]
    assert len(failed) >= 2


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/chaos/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_experiments"] == 4
    assert data["total_runs"] == 8
    # 5 passed, 3 failed out of 8 runs
    assert data["pass_rate"] == 62.5
    assert data["by_type"]["latency-injection"] == 1
    assert data["by_result"]["passed"] == 5
    assert data["by_result"]["failed"] == 3
