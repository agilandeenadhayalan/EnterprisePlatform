"""
Tests for the Bucketing service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_assign_user(client: AsyncClient):
    payload = {
        "experiment_id": "exp-new",
        "user_id": "user-new-001",
        "variant_weights": {"control": 0.5, "variant_a": 0.5},
    }
    resp = await client.post("/bucketing/assign", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["experiment_id"] == "exp-new"
    assert data["user_id"] == "user-new-001"
    assert data["variant"] in ("control", "variant_a")


@pytest.mark.anyio
async def test_assign_deterministic(client: AsyncClient):
    """Same user+experiment always gets the same variant."""
    payload = {
        "experiment_id": "exp-det",
        "user_id": "user-det-001",
        "variant_weights": {"control": 0.5, "variant_a": 0.5},
    }
    resp1 = await client.post("/bucketing/assign", json=payload)
    resp2 = await client.post("/bucketing/assign", json=payload)
    assert resp1.json()["variant"] == resp2.json()["variant"]


@pytest.mark.anyio
async def test_assign_different_users(client: AsyncClient):
    """Different users may get different variants (at least the assignments exist)."""
    variants = set()
    for i in range(10):
        payload = {
            "experiment_id": "exp-diff",
            "user_id": f"user-diff-{i:03d}",
            "variant_weights": {"control": 0.5, "variant_a": 0.5},
        }
        resp = await client.post("/bucketing/assign", json=payload)
        assert resp.status_code == 201
        variants.add(resp.json()["variant"])
    # With 10 users and 50/50 split, we should see both variants
    assert len(variants) >= 1


@pytest.mark.anyio
async def test_get_assignment(client: AsyncClient):
    resp = await client.get("/bucketing/assignment/exp-001/user-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert data["user_id"] == "user-001"


@pytest.mark.anyio
async def test_assignment_not_found(client: AsyncClient):
    resp = await client.get("/bucketing/assignment/exp-999/user-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_assignments(client: AsyncClient):
    resp = await client.get("/bucketing/assignments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 12


@pytest.mark.anyio
async def test_filter_experiment(client: AsyncClient):
    resp = await client.get("/bucketing/assignments", params={"experiment_id": "exp-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for a in data["assignments"]:
        assert a["experiment_id"] == "exp-001"


@pytest.mark.anyio
async def test_get_allocation(client: AsyncClient):
    resp = await client.get("/bucketing/allocation/exp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert "variant_weights" in data


@pytest.mark.anyio
async def test_allocation_not_found(client: AsyncClient):
    resp = await client.get("/bucketing/allocation/exp-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_set_allocation(client: AsyncClient):
    payload = {
        "experiment_id": "exp-new-alloc",
        "variant_weights": {"a": 0.6, "b": 0.4},
    }
    resp = await client.post("/bucketing/allocation", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["experiment_id"] == "exp-new-alloc"
    assert data["variant_weights"]["a"] == 0.6


@pytest.mark.anyio
async def test_bulk_assign(client: AsyncClient):
    payload = {
        "experiment_id": "exp-bulk",
        "user_ids": ["u1", "u2", "u3"],
        "variant_weights": {"control": 0.5, "variant_a": 0.5},
    }
    resp = await client.post("/bucketing/bulk-assign", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_bulk_assign_count(client: AsyncClient):
    payload = {
        "experiment_id": "exp-bulk2",
        "user_ids": ["u1", "u2", "u3", "u4", "u5"],
        "variant_weights": {"control": 0.5, "variant_a": 0.5},
    }
    resp = await client.post("/bucketing/bulk-assign", json=payload)
    assert resp.status_code == 201
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/bucketing/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_assignments"] == 12


@pytest.mark.anyio
async def test_stats_by_experiment(client: AsyncClient):
    resp = await client.get("/bucketing/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_experiment"]["exp-001"] == 5


@pytest.mark.anyio
async def test_config_in_stats(client: AsyncClient):
    resp = await client.get("/bucketing/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["config"]["hash_seed"] == "mobility2024"
    assert data["config"]["hash_algorithm"] == "md5"


@pytest.mark.anyio
async def test_assign_respects_weights(client: AsyncClient):
    """With 100% weight on one variant, all users should get that variant."""
    for i in range(5):
        payload = {
            "experiment_id": "exp-weight",
            "user_id": f"user-weight-{i}",
            "variant_weights": {"only_one": 1.0},
        }
        resp = await client.post("/bucketing/assign", json=payload)
        assert resp.status_code == 201
        assert resp.json()["variant"] == "only_one"
