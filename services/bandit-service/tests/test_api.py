"""
Tests for the Bandit service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_bandit(client: AsyncClient):
    payload = {
        "name": "New Bandit",
        "algorithm": "epsilon_greedy",
        "arms": [{"name": "arm_a"}, {"name": "arm_b"}],
        "epsilon": 0.2,
    }
    resp = await client.post("/bandits", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Bandit"
    assert data["algorithm"] == "epsilon_greedy"


@pytest.mark.anyio
async def test_list_bandits(client: AsyncClient):
    resp = await client.get("/bandits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_get_bandit(client: AsyncClient):
    resp = await client.get("/bandits/bandit-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Homepage CTA"
    assert data["algorithm"] == "epsilon_greedy"


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/bandits/bandit-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_pull_epsilon_greedy(client: AsyncClient):
    resp = await client.post("/bandits/bandit-001/pull")
    assert resp.status_code == 200
    data = resp.json()
    assert data["arm_selected"] in ("red_button", "blue_button", "green_button")
    assert data["experiment_id"] == "bandit-001"


@pytest.mark.anyio
async def test_pull_ucb1(client: AsyncClient):
    resp = await client.post("/bandits/bandit-002/pull")
    assert resp.status_code == 200
    data = resp.json()
    assert data["arm_selected"] in ("monthly", "annual", "lifetime", "trial")


@pytest.mark.anyio
async def test_pull_thompson(client: AsyncClient):
    resp = await client.post("/bandits/bandit-003/pull")
    assert resp.status_code == 200
    data = resp.json()
    assert data["arm_selected"] in ("urgent", "friendly", "formal")


@pytest.mark.anyio
async def test_pull_not_found(client: AsyncClient):
    resp = await client.post("/bandits/bandit-999/pull")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_reward_success(client: AsyncClient):
    payload = {"arm_name": "blue_button", "reward": 1.0, "success": True}
    resp = await client.post("/bandits/bandit-001/reward", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["updated_arm"]["successes"] == 63  # was 62


@pytest.mark.anyio
async def test_reward_failure(client: AsyncClient):
    payload = {"arm_name": "red_button", "reward": 0.0, "success": False}
    resp = await client.post("/bandits/bandit-001/reward", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["updated_arm"]["failures"] == 156  # was 155


@pytest.mark.anyio
async def test_reward_not_found_arm(client: AsyncClient):
    payload = {"arm_name": "nonexistent", "reward": 1.0, "success": True}
    resp = await client.post("/bandits/bandit-001/reward", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_decisions(client: AsyncClient):
    resp = await client.get("/bandits/bandit-001/decisions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for d in data["decisions"]:
        assert d["experiment_id"] == "bandit-001"


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/bandits/bandit-001/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "bandit-001"
    assert len(data["arms"]) == 3


@pytest.mark.anyio
async def test_stats_success_rates(client: AsyncClient):
    resp = await client.get("/bandits/bandit-001/stats")
    assert resp.status_code == 200
    data = resp.json()
    for arm in data["arms"]:
        if arm["name"] == "blue_button":
            assert arm["success_rate"] == pytest.approx(62 / 200, abs=0.01)
            assert arm["avg_reward"] == pytest.approx(62 / 200, abs=0.01)


@pytest.mark.anyio
async def test_reset(client: AsyncClient):
    resp = await client.post("/bandits/bandit-001/reset")
    assert resp.status_code == 200
    data = resp.json()
    for arm in data["arms"]:
        assert arm["pulls"] == 0
        assert arm["successes"] == 0


@pytest.mark.anyio
async def test_reset_clears_counts(client: AsyncClient):
    await client.post("/bandits/bandit-001/reset")
    resp = await client.get("/bandits/bandit-001/stats")
    data = resp.json()
    for arm in data["arms"]:
        assert arm["successes"] == 0
        assert arm["failures"] == 0
        assert arm["total_reward"] == 0.0
        assert arm["pulls"] == 0


@pytest.mark.anyio
async def test_pull_returns_arm_name(client: AsyncClient):
    resp = await client.post("/bandits/bandit-001/pull")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["arm_selected"], str)
    assert len(data["arm_selected"]) > 0
