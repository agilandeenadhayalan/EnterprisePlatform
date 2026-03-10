"""
Tests for the Traffic Simulator API.

Covers: run management, stepping, congestion map, incidents,
        route conditions, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_RUN = {
    "num_segments": 5,
    "config": {"city": "new_york", "time_of_day": "rush_hour"},
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_run(client: AsyncClient):
    """Start a traffic simulation."""
    resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    assert resp.status_code == 201
    data = resp.json()
    assert data["num_segments"] == 5
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.anyio
async def test_list_runs(client: AsyncClient):
    """List all runs."""
    await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)

    resp = await client.get("/simulation/traffic/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_run(client: AsyncClient):
    """Get run details."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/traffic/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.anyio
async def test_get_run_not_found(client: AsyncClient):
    """Getting non-existent run returns 404."""
    resp = await client.get("/simulation/traffic/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_step_simulation(client: AsyncClient):
    """Step traffic simulation."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.post(f"/simulation/traffic/runs/{run_id}/step")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] == 1
    assert data["segments_updated"] == 5
    assert data["status"] == "running"
    assert data["avg_speed"] > 0


@pytest.mark.anyio
async def test_step_not_found(client: AsyncClient):
    """Stepping non-existent run returns 404."""
    resp = await client.post("/simulation/traffic/runs/nonexistent/step")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_congestion_map(client: AsyncClient):
    """Get congestion map."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/traffic/runs/{run_id}/congestion")
    assert resp.status_code == 200
    congestion = resp.json()
    assert len(congestion) == 5
    assert all("congestion_level" in c for c in congestion)
    assert all("current_speed" in c for c in congestion)


@pytest.mark.anyio
async def test_congestion_not_found(client: AsyncClient):
    """Congestion for non-existent run returns 404."""
    resp = await client.get("/simulation/traffic/runs/nonexistent/congestion")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_inject_incident(client: AsyncClient):
    """Inject a traffic incident."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    # Get a segment ID
    congestion = await client.get(f"/simulation/traffic/runs/{run_id}/congestion")
    segment_id = congestion.json()[0]["segment_id"]

    resp = await client.post(f"/simulation/traffic/runs/{run_id}/incident", json={
        "segment_id": segment_id,
        "incident_type": "accident",
        "severity": 3,
        "impact_radius": 2.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["incident_type"] == "accident"
    assert data["severity"] == 3


@pytest.mark.anyio
async def test_inject_incident_not_found(client: AsyncClient):
    """Injecting incident for non-existent run returns 404."""
    resp = await client.post("/simulation/traffic/runs/nonexistent/incident", json={
        "segment_id": "seg-1",
        "incident_type": "accident",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_incident_affects_speed(client: AsyncClient):
    """Incidents reduce speed on affected segments."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    # Get initial speed
    congestion_before = await client.get(f"/simulation/traffic/runs/{run_id}/congestion")
    segment = congestion_before.json()[0]
    segment_id = segment["segment_id"]
    initial_speed = segment["current_speed"]

    # Inject severe incident
    await client.post(f"/simulation/traffic/runs/{run_id}/incident", json={
        "segment_id": segment_id,
        "incident_type": "accident",
        "severity": 5,
    })

    # Step to apply effects
    await client.post(f"/simulation/traffic/runs/{run_id}/step")

    congestion_after = await client.get(f"/simulation/traffic/runs/{run_id}/congestion")
    affected = [c for c in congestion_after.json() if c["segment_id"] == segment_id][0]
    # Speed should generally be reduced (though random factors exist)
    assert affected["current_speed"] <= initial_speed


@pytest.mark.anyio
async def test_route_conditions(client: AsyncClient):
    """Get route conditions."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    resp = await client.get(f"/simulation/traffic/runs/{run_id}/routes")
    assert resp.status_code == 200
    routes = resp.json()
    assert len(routes) == 5
    assert all("travel_time_factor" in r for r in routes)
    assert all(r["travel_time_factor"] >= 1.0 for r in routes)


@pytest.mark.anyio
async def test_route_conditions_not_found(client: AsyncClient):
    """Route conditions for non-existent run returns 404."""
    resp = await client.get("/simulation/traffic/runs/nonexistent/routes")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_multiple_steps(client: AsyncClient):
    """Multiple steps increment tick count."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    await client.post(f"/simulation/traffic/runs/{run_id}/step")
    await client.post(f"/simulation/traffic/runs/{run_id}/step")
    resp = await client.post(f"/simulation/traffic/runs/{run_id}/step")
    assert resp.json()["tick"] == 3

    run_resp = await client.get(f"/simulation/traffic/runs/{run_id}")
    assert run_resp.json()["num_ticks"] == 3


@pytest.mark.anyio
async def test_congestion_levels_in_map(client: AsyncClient):
    """Congestion map shows valid congestion levels."""
    create_resp = await client.post("/simulation/traffic/runs", json=SAMPLE_RUN)
    run_id = create_resp.json()["id"]

    valid_levels = ["free_flow", "light", "moderate", "heavy", "gridlock"]
    congestion = await client.get(f"/simulation/traffic/runs/{run_id}/congestion")
    for c in congestion.json():
        assert c["congestion_level"] in valid_levels


@pytest.mark.anyio
async def test_create_run_with_config(client: AsyncClient):
    """Create run with custom config."""
    resp = await client.post("/simulation/traffic/runs", json={
        "num_segments": 3,
        "config": {"weather": "rain", "visibility": 0.5},
    })
    assert resp.status_code == 201
    assert resp.json()["config"]["weather"] == "rain"
    assert resp.json()["num_segments"] == 3
