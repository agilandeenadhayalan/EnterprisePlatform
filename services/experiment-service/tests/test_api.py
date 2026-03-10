"""
Tests for the Experiment service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_experiment(client: AsyncClient):
    payload = {
        "name": "New Test Experiment",
        "description": "A test experiment",
        "experiment_type": "ab_test",
        "variants": [{"name": "control", "weight": 0.5, "config": {}}, {"name": "variant_a", "weight": 0.5, "config": {}}],
        "traffic_percentage": 100.0,
    }
    resp = await client.post("/experiments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Test Experiment"
    assert data["status"] == "draft"


@pytest.mark.anyio
async def test_list_experiments(client: AsyncClient):
    resp = await client.get("/experiments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["experiments"]) == 6


@pytest.mark.anyio
async def test_filter_by_status(client: AsyncClient):
    resp = await client.get("/experiments", params={"status": "running"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for e in data["experiments"]:
        assert e["status"] == "running"


@pytest.mark.anyio
async def test_filter_by_type(client: AsyncClient):
    resp = await client.get("/experiments", params={"experiment_type": "ab_test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for e in data["experiments"]:
        assert e["experiment_type"] == "ab_test"


@pytest.mark.anyio
async def test_get_experiment(client: AsyncClient):
    resp = await client.get("/experiments/exp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Checkout Button Color"
    assert data["experiment_type"] == "ab_test"


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/experiments/exp-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_experiment(client: AsyncClient):
    payload = {"name": "Updated Name", "description": "Updated desc"}
    resp = await client.put("/experiments/exp-001", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated desc"


@pytest.mark.anyio
async def test_update_not_found(client: AsyncClient):
    payload = {"name": "Updated Name"}
    resp = await client.put("/experiments/exp-999", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_start_experiment(client: AsyncClient):
    resp = await client.post("/experiments/exp-005/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_start_invalid_status(client: AsyncClient):
    # exp-002 is completed, cannot start
    resp = await client.post("/experiments/exp-002/start")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_pause_experiment(client: AsyncClient):
    resp = await client.post("/experiments/exp-001/pause")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "paused"


@pytest.mark.anyio
async def test_pause_invalid(client: AsyncClient):
    # exp-005 is draft, cannot pause
    resp = await client.post("/experiments/exp-005/pause")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_complete_experiment(client: AsyncClient):
    resp = await client.post("/experiments/exp-001/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_complete_invalid(client: AsyncClient):
    # exp-005 is draft, cannot complete
    resp = await client.post("/experiments/exp-005/complete")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_archive_experiment(client: AsyncClient):
    resp = await client.delete("/experiments/exp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "archived"


@pytest.mark.anyio
async def test_archive_not_found(client: AsyncClient):
    resp = await client.delete("/experiments/exp-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/experiments/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert "by_status" in data
    assert "by_type" in data


@pytest.mark.anyio
async def test_stats_by_type(client: AsyncClient):
    resp = await client.get("/experiments/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_type"]["ab_test"] == 2
    assert data["by_type"]["feature_flag"] == 2
