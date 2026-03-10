"""
Tests for the Load Test Service API.

Covers: scenario CRUD, run management, result recording, latency analysis,
        percentile calculations, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_SCENARIO = {
    "name": "API Gateway Ramp Test",
    "pattern": "ramp",
    "target_rps": 500,
    "duration_seconds": 120,
    "config": {"endpoint": "/api/v1/trips", "method": "GET"},
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_scenario(client: AsyncClient):
    """Create a load test scenario."""
    resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Gateway Ramp Test"
    assert data["pattern"] == "ramp"
    assert data["target_rps"] == 500
    assert "id" in data


@pytest.mark.anyio
async def test_list_scenarios(client: AsyncClient):
    """List all scenarios."""
    await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    await client.post("/load-tests/scenarios", json={
        **SAMPLE_SCENARIO, "name": "Spike Test", "pattern": "spike",
    })

    resp = await client.get("/load-tests/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_start_run(client: AsyncClient):
    """Start a load test run."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]

    resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["scenario_id"] == scenario_id
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_start_run_invalid_scenario(client: AsyncClient):
    """Starting run with invalid scenario returns 404."""
    resp = await client.post("/load-tests/runs", json={"scenario_id": "nonexistent"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    """List all runs."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]

    await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    await client.post("/load-tests/runs", json={"scenario_id": scenario_id})

    resp = await client.get("/load-tests/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_run(client: AsyncClient):
    """Get run details."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    resp = await client.get(f"/load-tests/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.anyio
async def test_get_run_not_found(client: AsyncClient):
    """Getting non-existent run returns 404."""
    resp = await client.get("/load-tests/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_run(client: AsyncClient):
    """Update run status."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    resp = await client.patch(f"/load-tests/runs/{run_id}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.anyio
async def test_record_results(client: AsyncClient):
    """Record results for a run."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    resp = await client.post(f"/load-tests/runs/{run_id}/results", json={
        "p50_ms": 12.5,
        "p95_ms": 45.0,
        "p99_ms": 120.0,
        "error_rate": 0.02,
        "total_requests": 10000,
        "throughput_rps": 450.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["p50_ms"] == 12.5
    assert data["p99_ms"] == 120.0
    assert data["total_requests"] == 10000


@pytest.mark.anyio
async def test_record_results_invalid_run(client: AsyncClient):
    """Recording results for invalid run returns 404."""
    resp = await client.post("/load-tests/runs/nonexistent/results", json={
        "p50_ms": 10.0,
        "p95_ms": 20.0,
        "p99_ms": 30.0,
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_analysis(client: AsyncClient):
    """Get latency analysis for a run."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    # Record two batches of results
    await client.post(f"/load-tests/runs/{run_id}/results", json={
        "p50_ms": 10.0, "p95_ms": 40.0, "p99_ms": 100.0,
        "error_rate": 0.01, "total_requests": 5000, "throughput_rps": 400.0,
    })
    await client.post(f"/load-tests/runs/{run_id}/results", json={
        "p50_ms": 20.0, "p95_ms": 60.0, "p99_ms": 150.0,
        "error_rate": 0.03, "total_requests": 5000, "throughput_rps": 500.0,
    })

    resp = await client.get(f"/load-tests/runs/{run_id}/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["num_results"] == 2
    assert data["avg_p50_ms"] == 15.0
    assert data["avg_p95_ms"] == 50.0
    assert data["avg_p99_ms"] == 125.0
    assert data["total_requests"] == 10000


@pytest.mark.anyio
async def test_analysis_empty(client: AsyncClient):
    """Analysis with no results returns zeros."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    resp = await client.get(f"/load-tests/runs/{run_id}/analysis")
    assert resp.status_code == 200
    assert resp.json()["num_results"] == 0
    assert resp.json()["avg_p50_ms"] == 0.0


@pytest.mark.anyio
async def test_analysis_not_found(client: AsyncClient):
    """Analysis for non-existent run returns 404."""
    resp = await client.get("/load-tests/runs/nonexistent/analysis")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_results_appear_in_run(client: AsyncClient):
    """Results are included in run details."""
    scenario_resp = await client.post("/load-tests/scenarios", json=SAMPLE_SCENARIO)
    scenario_id = scenario_resp.json()["id"]
    run_resp = await client.post("/load-tests/runs", json={"scenario_id": scenario_id})
    run_id = run_resp.json()["id"]

    await client.post(f"/load-tests/runs/{run_id}/results", json={
        "p50_ms": 10.0, "p95_ms": 30.0, "p99_ms": 80.0,
        "total_requests": 1000, "throughput_rps": 100.0,
    })

    resp = await client.get(f"/load-tests/runs/{run_id}")
    assert len(resp.json()["results"]) == 1


@pytest.mark.anyio
async def test_scenario_with_config(client: AsyncClient):
    """Create scenario with custom config."""
    resp = await client.post("/load-tests/scenarios", json={
        **SAMPLE_SCENARIO,
        "config": {"headers": {"Authorization": "Bearer token"}, "timeout": 30},
    })
    assert resp.status_code == 201
    assert resp.json()["config"]["timeout"] == 30
