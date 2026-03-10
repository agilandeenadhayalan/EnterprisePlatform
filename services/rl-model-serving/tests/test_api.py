"""
Tests for the RL Model Serving service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_predict(client: AsyncClient):
    payload = {
        "model_id": "model-001",
        "state_input": {"driver_pos": [2, 3], "request_pos": [5, 5]},
    }
    resp = await client.post("/rl-models/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "model-001"
    assert isinstance(data["action_output"], str)
    assert data["confidence"] > 0


@pytest.mark.anyio
async def test_predict_not_found(client: AsyncClient):
    payload = {
        "model_id": "model-999",
        "state_input": {"pos": [0, 0]},
    }
    resp = await client.post("/rl-models/predict", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_models(client: AsyncClient):
    resp = await client.get("/rl-models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4


@pytest.mark.anyio
async def test_filter_status(client: AsyncClient):
    resp = await client.get("/rl-models", params={"status": "active"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for m in data["models"]:
        assert m["status"] == "active"


@pytest.mark.anyio
async def test_filter_algorithm(client: AsyncClient):
    resp = await client.get("/rl-models", params={"algorithm": "q_learning"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for m in data["models"]:
        assert m["algorithm"] == "q_learning"


@pytest.mark.anyio
async def test_get_model(client: AsyncClient):
    resp = await client.get("/rl-models/model-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Q-Learning Dispatch"
    assert data["version"] == "v1"


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/rl-models/model-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_register_model(client: AsyncClient):
    payload = {
        "name": "New Model",
        "version": "v1",
        "algorithm": "ppo",
        "metrics": {"avg_reward": 0.90},
    }
    resp = await client.post("/rl-models", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Model"
    assert data["status"] == "staging"


@pytest.mark.anyio
async def test_promote(client: AsyncClient):
    resp = await client.post("/rl-models/model-003/promote")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_promote_not_found(client: AsyncClient):
    resp = await client.post("/rl-models/model-999/promote")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_retire(client: AsyncClient):
    resp = await client.post("/rl-models/model-001/retire")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "retired"


@pytest.mark.anyio
async def test_retire_not_found(client: AsyncClient):
    resp = await client.post("/rl-models/model-999/retire")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_compare(client: AsyncClient):
    payload = {
        "model_a_id": "model-001",
        "model_b_id": "model-002",
        "metric": "avg_reward",
    }
    resp = await client.post("/rl-models/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_a_value"] == 0.72
    assert data["model_b_value"] == 0.81


@pytest.mark.anyio
async def test_compare_winner(client: AsyncClient):
    payload = {
        "model_a_id": "model-001",
        "model_b_id": "model-002",
        "metric": "avg_reward",
    }
    resp = await client.post("/rl-models/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["winner"] == "model-002"


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/rl-models/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_models"] == 4
    assert data["total_predictions"] == 6


@pytest.mark.anyio
async def test_stats_by_status(client: AsyncClient):
    resp = await client.get("/rl-models/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_status"]["active"] == 2
    assert data["by_status"]["staging"] == 1
    assert data["by_status"]["retired"] == 1
