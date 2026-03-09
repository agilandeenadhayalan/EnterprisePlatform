"""
Tests for the Deployment service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_deployments(client: AsyncClient):
    resp = await client.get("/deployments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["deployments"]) == 6


@pytest.mark.anyio
async def test_list_filter_environment(client: AsyncClient):
    resp = await client.get("/deployments", params={"environment": "production"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for d in data["deployments"]:
        assert d["environment"] == "production"


@pytest.mark.anyio
async def test_list_filter_strategy(client: AsyncClient):
    resp = await client.get("/deployments", params={"strategy": "canary"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for d in data["deployments"]:
        assert d["strategy"] == "canary"


@pytest.mark.anyio
async def test_list_filter_status(client: AsyncClient):
    resp = await client.get("/deployments", params={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for d in data["deployments"]:
        assert d["status"] == "completed"


@pytest.mark.anyio
async def test_create_deployment(client: AsyncClient):
    payload = {
        "service_name": "analytics-service",
        "version": "v1.0.0",
        "strategy": "rolling",
        "environment": "dev",
    }
    resp = await client.post("/deployments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] == "analytics-service"
    assert data["version"] == "v1.0.0"
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_create_canary(client: AsyncClient):
    payload = {
        "service_name": "search-service",
        "version": "v2.0.0",
        "strategy": "canary",
        "environment": "staging",
    }
    resp = await client.post("/deployments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["strategy"] == "canary"


@pytest.mark.anyio
async def test_get_deployment(client: AsyncClient):
    resp = await client.get("/deployments/dep-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "auth-service"
    assert data["version"] == "v2.1.0"
    assert data["strategy"] == "blue-green"


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/deployments/dep-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_rollback(client: AsyncClient):
    resp = await client.post("/deployments/dep-001/rollback")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rolled-back"
    assert data["rolled_back"] is True


@pytest.mark.anyio
async def test_rollback_not_found(client: AsyncClient):
    resp = await client.post("/deployments/dep-999/rollback")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_rollback_already_rolled_back(client: AsyncClient):
    # First rollback
    await client.post("/deployments/dep-001/rollback")
    # Second rollback should fail
    resp = await client.post("/deployments/dep-001/rollback")
    assert resp.status_code == 400
    assert "already rolled back" in resp.json()["detail"]


@pytest.mark.anyio
async def test_deployment_history(client: AsyncClient):
    resp = await client.get("/deployments/dep-001/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    actions = [e["action"] for e in data["events"]]
    assert "created" in actions
    assert "completed" in actions


@pytest.mark.anyio
async def test_promote_dev_to_staging(client: AsyncClient):
    # dep-003 is completed in dev
    resp = await client.post("/deployments/dep-003/promote")
    assert resp.status_code == 201
    data = resp.json()
    assert data["environment"] == "staging"
    assert data["service_name"] == "payment-service"
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_promote_production_error(client: AsyncClient):
    # dep-001 is completed in production
    resp = await client.post("/deployments/dep-001/promote")
    assert resp.status_code == 400
    assert "production" in resp.json()["detail"]


@pytest.mark.anyio
async def test_environments(client: AsyncClient):
    resp = await client.get("/deployments/environments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    names = [e["name"] for e in data["environments"]]
    assert "dev" in names
    assert "staging" in names
    assert "production" in names


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/deployments/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert data["by_status"]["completed"] == 4
    assert data["rollback_rate"] == 0.0


@pytest.mark.anyio
async def test_create_then_list(client: AsyncClient):
    payload = {
        "service_name": "new-service",
        "version": "v0.1.0",
        "strategy": "rolling",
        "environment": "dev",
    }
    await client.post("/deployments", json=payload)
    resp = await client.get("/deployments")
    assert resp.json()["total"] == 7
