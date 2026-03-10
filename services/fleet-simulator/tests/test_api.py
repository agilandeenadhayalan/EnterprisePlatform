"""
Tests for the Fleet Simulator API.

Covers: run management, driver states, demand injection, stepping,
        supply/demand analytics, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_RUN = {
    "num_drivers": 5,
    "config": {"city": "new_york"},
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_run(client: AsyncClient):
    """Start a fleet simulation."""
    resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    assert resp.status_code == 201
    data = resp.json()
    assert data["num_drivers"] == 5
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    """List all runs."""
    await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)

    resp = await client.get("/simulation/fleet/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_run(client: AsyncClient):
    """Get run details."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/fleet/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.anyio
async def test_get_run_not_found(client: AsyncClient):
    """Getting non-existent run returns 404."""
    resp = await client.get("/simulation/fleet/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_drivers(client: AsyncClient):
    """Get driver states."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/fleet/runs/{run_id}/drivers")
    assert resp.status_code == 200
    drivers = resp.json()
    assert len(drivers) == 5
    assert all(d["state"] == "idle" for d in drivers)


@pytest.mark.anyio
async def test_step_simulation(client: AsyncClient):
    """Step fleet simulation."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.post(f"/simulation/fleet/runs/{run_id}/step")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] == 1
    assert data["drivers_moved"] == 5
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_step_not_found(client: AsyncClient):
    """Stepping non-existent run returns 404."""
    resp = await client.post("/simulation/fleet/runs/nonexistent/step")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_inject_demand(client: AsyncClient):
    """Inject a demand event."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.post(f"/simulation/fleet/runs/{run_id}/demand", json={
        "pickup": {"lat": 40.7128, "lon": -74.0060},
        "dropoff": {"lat": 40.7580, "lon": -73.9855},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["run_id"] == run_id
    assert "pickup" in data
    assert "dropoff" in data


@pytest.mark.anyio
async def test_inject_demand_not_found(client: AsyncClient):
    """Injecting demand for non-existent run returns 404."""
    resp = await client.post("/simulation/fleet/runs/nonexistent/demand", json={})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_supply_demand_initial(client: AsyncClient):
    """Supply/demand analytics at start."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/fleet/runs/{run_id}/supply-demand")
    assert resp.status_code == 200
    data = resp.json()
    assert data["idle_drivers"] == 5
    assert data["active_drivers"] == 0
    assert data["pending_requests"] == 0
    assert data["utilization_rate"] == 0.0


@pytest.mark.anyio
async def test_supply_demand_after_demand(client: AsyncClient):
    """Supply/demand changes after injecting demand and stepping."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    # Inject demand
    await client.post(f"/simulation/fleet/runs/{run_id}/demand", json={
        "pickup": {"lat": 40.71, "lon": -74.01},
        "dropoff": {"lat": 40.75, "lon": -73.98},
    })

    # Step to process demand
    await client.post(f"/simulation/fleet/runs/{run_id}/step")

    resp = await client.get(f"/simulation/fleet/runs/{run_id}/supply-demand")
    data = resp.json()
    assert data["active_drivers"] >= 1
    assert data["utilization_rate"] > 0


@pytest.mark.anyio
async def test_supply_demand_not_found(client: AsyncClient):
    """Supply/demand for non-existent run returns 404."""
    resp = await client.get("/simulation/fleet/runs/nonexistent/supply-demand")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_multiple_steps(client: AsyncClient):
    """Multiple steps increment tick count."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    await client.post(f"/simulation/fleet/runs/{run_id}/step")
    await client.post(f"/simulation/fleet/runs/{run_id}/step")
    resp = await client.post(f"/simulation/fleet/runs/{run_id}/step")
    assert resp.json()["tick"] == 3

    run_resp = await client.get(f"/simulation/fleet/runs/{run_id}")
    assert run_resp.json()["num_ticks"] == 3


@pytest.mark.anyio
async def test_drivers_have_positions(client: AsyncClient):
    """Drivers have position data."""
    create_resp = await client.post("/simulation/fleet/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/fleet/runs/{run_id}/drivers")
    for driver in resp.json():
        assert "lat" in driver["position"]
        assert "lon" in driver["position"]


@pytest.mark.anyio
async def test_create_run_with_config(client: AsyncClient):
    """Create run with custom config."""
    resp = await client.post("/simulation/fleet/runs", json={
        "num_drivers": 20,
        "config": {"surge_multiplier": 1.5, "area": "manhattan"},
    })
    assert resp.status_code == 201
    assert resp.json()["config"]["surge_multiplier"] == 1.5
