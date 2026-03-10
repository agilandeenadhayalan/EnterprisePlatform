"""
Tests for the City Simulator API.

Covers: run CRUD, agent management, simulation stepping, metrics,
        pause/resume/stop, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_RUN = {
    "simulation_type": "city",
    "scenario": {"city": "new_york", "peak_hours": True},
    "num_agents": 0,
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_run(client: AsyncClient):
    """Create a simulation run."""
    resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    assert resp.status_code == 201
    data = resp.json()
    assert data["simulation_type"] == "city"
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    """List all runs."""
    await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    await client.post("/simulation/city/runs", json=SAMPLE_RUN)

    resp = await client.get("/simulation/city/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_run(client: AsyncClient):
    """Get run details."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/city/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.anyio
async def test_get_run_not_found(client: AsyncClient):
    """Getting non-existent run returns 404."""
    resp = await client.get("/simulation/city/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_run_pause(client: AsyncClient):
    """Pause a simulation run."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.patch(f"/simulation/city/runs/{run_id}", json={"status": "paused"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.anyio
async def test_update_run_stop(client: AsyncClient):
    """Stop a simulation run sets completed_at."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.patch(f"/simulation/city/runs/{run_id}", json={"status": "stopped"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert resp.json()["completed_at"] is not None


@pytest.mark.anyio
async def test_add_agents(client: AsyncClient):
    """Add agents to a simulation."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver",
        "count": 5,
    })
    assert resp.status_code == 201
    assert len(resp.json()) == 5
    assert all(a["agent_type"] == "driver" for a in resp.json())


@pytest.mark.anyio
async def test_add_agents_not_found(client: AsyncClient):
    """Adding agents to non-existent run returns 404."""
    resp = await client.post("/simulation/city/runs/nonexistent/agents", json={
        "agent_type": "driver",
        "count": 1,
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_agents(client: AsyncClient):
    """List agents in a run."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver", "count": 3,
    })
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "rider", "count": 2,
    })

    resp = await client.get(f"/simulation/city/runs/{run_id}/agents")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


@pytest.mark.anyio
async def test_step_simulation(client: AsyncClient):
    """Advance simulation by one tick."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver", "count": 5,
    })

    resp = await client.post(f"/simulation/city/runs/{run_id}/step")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] == 1
    assert data["agents_moved"] == 5
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_multiple_steps(client: AsyncClient):
    """Multiple simulation steps increment tick count."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver", "count": 3,
    })

    await client.post(f"/simulation/city/runs/{run_id}/step")
    await client.post(f"/simulation/city/runs/{run_id}/step")
    resp = await client.post(f"/simulation/city/runs/{run_id}/step")
    assert resp.json()["tick"] == 3

    run_resp = await client.get(f"/simulation/city/runs/{run_id}")
    assert run_resp.json()["num_ticks"] == 3


@pytest.mark.anyio
async def test_step_not_found(client: AsyncClient):
    """Stepping non-existent run returns 404."""
    resp = await client.post("/simulation/city/runs/nonexistent/step")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_metrics(client: AsyncClient):
    """Get simulation metrics."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver", "count": 10,
    })
    await client.post(f"/simulation/city/runs/{run_id}/step")

    resp = await client.get(f"/simulation/city/runs/{run_id}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_trips" in data
    assert "utilization" in data
    assert "supply_demand_ratio" in data


@pytest.mark.anyio
async def test_metrics_not_found(client: AsyncClient):
    """Metrics for non-existent run returns 404."""
    resp = await client.get("/simulation/city/runs/nonexistent/metrics")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_agents_update_num_agents(client: AsyncClient):
    """Adding agents updates run num_agents."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "vehicle", "count": 4,
    })

    run_resp = await client.get(f"/simulation/city/runs/{run_id}")
    assert run_resp.json()["num_agents"] == 4


@pytest.mark.anyio
async def test_agent_positions(client: AsyncClient):
    """Agents have position data."""
    create_resp = await client.post("/simulation/city/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]
    await client.post(f"/simulation/city/runs/{run_id}/agents", json={
        "agent_type": "driver", "count": 1,
    })

    resp = await client.get(f"/simulation/city/runs/{run_id}/agents")
    agent = resp.json()[0]
    assert "lat" in agent["position"]
    assert "lon" in agent["position"]
