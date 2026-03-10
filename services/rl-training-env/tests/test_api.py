"""
Tests for the RL Training Environment service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_start_episode(client: AsyncClient):
    payload = {
        "env_name": "gridworld",
        "policy_id": "pol-test",
        "epsilon": 0.5,
    }
    resp = await client.post("/rl-training/episodes", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["env_name"] == "gridworld"
    assert data["status"] == "running"
    assert data["steps"] == 0


@pytest.mark.anyio
async def test_list_episodes(client: AsyncClient):
    resp = await client.get("/rl-training/episodes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6


@pytest.mark.anyio
async def test_filter_env(client: AsyncClient):
    resp = await client.get("/rl-training/episodes", params={"env_name": "gridworld"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for e in data["episodes"]:
        assert e["env_name"] == "gridworld"


@pytest.mark.anyio
async def test_filter_status(client: AsyncClient):
    resp = await client.get("/rl-training/episodes", params={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for e in data["episodes"]:
        assert e["status"] == "completed"


@pytest.mark.anyio
async def test_get_episode(client: AsyncClient):
    resp = await client.get("/rl-training/episodes/ep-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["env_name"] == "gridworld"
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/rl-training/episodes/ep-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_step(client: AsyncClient):
    payload = {
        "state": {"pos": [0, 0]},
        "action": "right",
        "reward": 0.5,
        "next_state": {"pos": [1, 0]},
        "done": False,
    }
    resp = await client.post("/rl-training/episodes/ep-004/step", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["episode_id"] == "ep-004"
    assert data["done"] is False


@pytest.mark.anyio
async def test_step_increments(client: AsyncClient):
    # ep-004 starts with 200 steps
    payload = {
        "state": {"pos": [0, 0]},
        "action": "right",
        "reward": 0.0,
        "next_state": {"pos": [1, 0]},
        "done": False,
    }
    resp = await client.post("/rl-training/episodes/ep-004/step", json=payload)
    data = resp.json()
    assert data["steps"] == 201


@pytest.mark.anyio
async def test_step_adds_reward(client: AsyncClient):
    # ep-004 starts with total_reward=0.0
    payload = {
        "state": {"pos": [0, 0]},
        "action": "right",
        "reward": 1.5,
        "next_state": {"pos": [1, 0]},
        "done": False,
    }
    resp = await client.post("/rl-training/episodes/ep-004/step", json=payload)
    data = resp.json()
    assert data["total_reward"] == 1.5


@pytest.mark.anyio
async def test_step_done_completes(client: AsyncClient):
    payload = {
        "state": {"pos": [2, 2]},
        "action": "pickup",
        "reward": 10.0,
        "next_state": {"pos": [2, 2]},
        "done": True,
    }
    resp = await client.post("/rl-training/episodes/ep-004/step", json=payload)
    data = resp.json()
    assert data["done"] is True
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_complete_episode(client: AsyncClient):
    resp = await client.post("/rl-training/episodes/ep-004/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.anyio
async def test_complete_not_found(client: AsyncClient):
    resp = await client.post("/rl-training/episodes/ep-999/complete")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_configs(client: AsyncClient):
    resp = await client.get("/rl-training/configs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_create_config(client: AsyncClient):
    payload = {
        "env_name": "new_env",
        "max_episodes": 500,
        "max_steps": 100,
        "learning_rate": 0.01,
        "discount_factor": 0.95,
        "epsilon_start": 1.0,
        "epsilon_end": 0.1,
        "buffer_size": 5000,
    }
    resp = await client.post("/rl-training/configs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["env_name"] == "new_env"
    assert data["max_episodes"] == 500


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/rl-training/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_episodes"] == 6
    assert "by_status" in data
    assert "avg_reward" in data
    assert "avg_steps" in data


@pytest.mark.anyio
async def test_stats_by_env(client: AsyncClient):
    resp = await client.get("/rl-training/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_env"]["gridworld"] == 2
    assert data["by_env"]["taxi"] == 2
    assert data["by_env"]["dispatch_sim"] == 2
