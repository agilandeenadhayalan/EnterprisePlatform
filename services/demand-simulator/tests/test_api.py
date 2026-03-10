"""
Tests for the Demand Simulator service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_scenario(client: AsyncClient):
    payload = {
        "name": "test_scenario",
        "pattern_type": "custom",
        "parameters": {"key": "value"},
        "duration_hours": 2,
    }
    resp = await client.post("/simulator/scenarios", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_scenario"
    assert data["pattern_type"] == "custom"


@pytest.mark.anyio
async def test_list_scenarios(client: AsyncClient):
    resp = await client.get("/simulator/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["scenarios"]) == 5


@pytest.mark.anyio
async def test_filter_pattern(client: AsyncClient):
    resp = await client.get("/simulator/scenarios", params={"pattern_type": "commute"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for s in data["scenarios"]:
        assert s["pattern_type"] == "commute"


@pytest.mark.anyio
async def test_get_scenario(client: AsyncClient):
    resp = await client.get("/simulator/scenarios/scenario-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "commute_morning"


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/simulator/scenarios/scenario-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_simulation(client: AsyncClient):
    resp = await client.post("/simulator/run/scenario-001")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert data["generated_events"] > 0


@pytest.mark.anyio
async def test_run_creates_events(client: AsyncClient):
    resp = await client.post("/simulator/run/scenario-001")
    assert resp.status_code == 201
    data = resp.json()
    assert data["generated_events"] > 0
    assert "avg_demand" in data["results"]


@pytest.mark.anyio
async def test_run_not_found_scenario(client: AsyncClient):
    resp = await client.post("/simulator/run/scenario-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    resp = await client.get("/simulator/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["runs"]) == 4


@pytest.mark.anyio
async def test_filter_status(client: AsyncClient):
    resp = await client.get("/simulator/runs", params={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for r in data["runs"]:
        assert r["status"] == "completed"


@pytest.mark.anyio
async def test_get_run(client: AsyncClient):
    resp = await client.get("/simulator/runs/run-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"] == "scenario-001"
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_run_not_found(client: AsyncClient):
    resp = await client.get("/simulator/runs/run-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/simulator/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_scenarios"] == 5
    assert data["total_runs"] == 4


@pytest.mark.anyio
async def test_stats_by_status(client: AsyncClient):
    resp = await client.get("/simulator/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_status"]["completed"] == 2
    assert data["by_status"]["running"] == 1
    assert data["by_status"]["failed"] == 1


@pytest.mark.anyio
async def test_simulation_generates_events(client: AsyncClient):
    resp = await client.post("/simulator/run/scenario-005")
    assert resp.status_code == 201
    data = resp.json()
    assert data["generated_events"] > 0
    assert data["results"]["avg_demand"] > 0
    assert data["results"]["peak_demand"] > 0
