"""
Tests for the RL Dispatch service API.
"""

import pytest
from httpx import AsyncClient
import repository


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_decide(client: AsyncClient):
    payload = {
        "state": {"grid_size": 10},
        "available_drivers": ["driver-100", "driver-101"],
        "pending_requests": ["req-100"],
    }
    resp = await client.post("/rl-dispatch/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "action" in data
    assert "policy_used" in data


@pytest.mark.anyio
async def test_decide_returns_action(client: AsyncClient):
    payload = {
        "state": {"grid_size": 10},
        "available_drivers": ["driver-100"],
        "pending_requests": ["req-100"],
    }
    resp = await client.post("/rl-dispatch/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"]["driver_id"] == "driver-100"
    assert data["action"]["request_id"] == "req-100"
    assert data["action"]["action_type"] == "assign"


@pytest.mark.anyio
async def test_decide_no_active_policy(client: AsyncClient):
    # Deactivate all policies
    for pid in list(repository.repo.policies.keys()):
        repository.repo.policies[pid].is_active = False
    payload = {
        "state": {},
        "available_drivers": ["d1"],
        "pending_requests": ["r1"],
    }
    resp = await client.post("/rl-dispatch/decide", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_actions(client: AsyncClient):
    resp = await client.get("/rl-dispatch/actions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8


@pytest.mark.anyio
async def test_filter_policy(client: AsyncClient):
    resp = await client.get("/rl-dispatch/actions", params={"policy_id": "pol-001"})
    assert resp.status_code == 200
    data = resp.json()
    for a in data["actions"]:
        assert a["policy_id"] == "pol-001"


@pytest.mark.anyio
async def test_get_action(client: AsyncClient):
    resp = await client.get("/rl-dispatch/actions/act-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["driver_id"] == "driver-001"


@pytest.mark.anyio
async def test_get_action_not_found(client: AsyncClient):
    resp = await client.get("/rl-dispatch/actions/act-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_reward(client: AsyncClient):
    payload = {"action_id": "act-001", "reward": 0.95}
    resp = await client.post("/rl-dispatch/reward", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["reward"] == 0.95
    assert data["updated"] is True


@pytest.mark.anyio
async def test_reward_not_found(client: AsyncClient):
    payload = {"action_id": "act-999", "reward": 0.5}
    resp = await client.post("/rl-dispatch/reward", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_policies(client: AsyncClient):
    resp = await client.get("/rl-dispatch/policies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_create_policy(client: AsyncClient):
    payload = {
        "name": "New Policy",
        "algorithm": "actor_critic",
        "parameters": {"lr": 0.001},
    }
    resp = await client.post("/rl-dispatch/policies", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Policy"
    assert data["is_active"] is False


@pytest.mark.anyio
async def test_activate_policy(client: AsyncClient):
    resp = await client.post("/rl-dispatch/policies/pol-002/activate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_activate_deactivates_others(client: AsyncClient):
    await client.post("/rl-dispatch/policies/pol-002/activate")
    resp = await client.get("/rl-dispatch/policies")
    data = resp.json()
    active_count = sum(1 for p in data["policies"] if p["is_active"])
    assert active_count == 1
    for p in data["policies"]:
        if p["id"] == "pol-002":
            assert p["is_active"] is True
        else:
            assert p["is_active"] is False


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/rl-dispatch/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_actions"] == 8


@pytest.mark.anyio
async def test_stats_avg_reward(client: AsyncClient):
    resp = await client.get("/rl-dispatch/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["avg_reward"] > 0


@pytest.mark.anyio
async def test_active_policy_in_stats(client: AsyncClient):
    resp = await client.get("/rl-dispatch/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_policy"] == "pol-001"
