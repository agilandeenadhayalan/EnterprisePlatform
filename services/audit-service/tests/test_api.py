"""
Tests for the Audit Service API.

Covers: log creation, query/filter, entity/actor lookups, search,
        hash chain integrity, stats, and immutability.
"""

import pytest
from httpx import AsyncClient


SAMPLE_LOG = {
    "action": "create",
    "entity_type": "user",
    "entity_id": "user-123",
    "actor": "admin@example.com",
    "details": {"field": "email", "new_value": "test@example.com"},
    "region": "us-east-1",
    "ip_address": "192.168.1.1",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_log(client: AsyncClient):
    """Record an audit event."""
    resp = await client.post("/audit/logs", json=SAMPLE_LOG)
    assert resp.status_code == 201
    data = resp.json()
    assert data["action"] == "create"
    assert data["entity_type"] == "user"
    assert data["actor"] == "admin@example.com"
    assert "id" in data
    assert "entry_hash" in data
    assert len(data["entry_hash"]) == 64  # SHA-256 hex


@pytest.mark.anyio
async def test_create_log_invalid_action(client: AsyncClient):
    """Invalid action returns 400."""
    resp = await client.post("/audit/logs", json={
        **SAMPLE_LOG, "action": "hack",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_log(client: AsyncClient):
    """Get a specific log entry."""
    create_resp = await client.post("/audit/logs", json=SAMPLE_LOG)
    log_id = create_resp.json()["id"]

    resp = await client.get(f"/audit/logs/{log_id}")
    assert resp.status_code == 200
    assert resp.json()["actor"] == "admin@example.com"


@pytest.mark.anyio
async def test_get_log_not_found(client: AsyncClient):
    """Getting non-existent log returns 404."""
    resp = await client.get("/audit/logs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_logs(client: AsyncClient):
    """List all audit logs."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "update"})

    resp = await client.get("/audit/logs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_logs_filter_by_action(client: AsyncClient):
    """Filter logs by action."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "delete"})

    resp = await client.get("/audit/logs?action=create")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["action"] == "create"


@pytest.mark.anyio
async def test_list_logs_filter_by_entity_type(client: AsyncClient):
    """Filter logs by entity type."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "entity_type": "order"})

    resp = await client.get("/audit/logs?entity_type=user")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_logs_for_entity(client: AsyncClient):
    """Get logs for a specific entity."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "update", "entity_id": "user-123"})
    await client.post("/audit/logs", json={**SAMPLE_LOG, "entity_id": "user-456"})

    resp = await client.get("/audit/logs/entity/user/user-123")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_logs_by_actor(client: AsyncClient):
    """Get logs by actor."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "actor": "other@example.com"})

    resp = await client.get("/audit/logs/actor/admin@example.com")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["actor"] == "admin@example.com"


@pytest.mark.anyio
async def test_search_logs(client: AsyncClient):
    """Advanced search with multiple filters."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={
        **SAMPLE_LOG, "action": "delete", "region": "eu-west-1",
    })

    resp = await client.post("/audit/logs/search", json={
        "action": "create",
        "region": "us-east-1",
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_hash_chain_integrity(client: AsyncClient):
    """Hash chain links consecutive entries."""
    resp1 = await client.post("/audit/logs", json=SAMPLE_LOG)
    hash1 = resp1.json()["entry_hash"]

    resp2 = await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "update"})
    assert resp2.json()["previous_hash"] == hash1


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    """Get audit statistics."""
    await client.post("/audit/logs", json=SAMPLE_LOG)
    await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "delete"})
    await client.post("/audit/logs", json={**SAMPLE_LOG, "action": "login", "entity_type": "session"})

    resp = await client.get("/audit/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entries"] == 3
    assert data["by_action"]["create"] == 1
    assert data["by_action"]["delete"] == 1
    assert data["chain_valid"] is True


@pytest.mark.anyio
async def test_stats_empty(client: AsyncClient):
    """Stats with no entries."""
    resp = await client.get("/audit/stats")
    assert resp.status_code == 200
    assert resp.json()["total_entries"] == 0
    assert resp.json()["chain_valid"] is True


@pytest.mark.anyio
async def test_all_action_types(client: AsyncClient):
    """All valid action types are accepted."""
    actions = ["create", "read", "update", "delete", "login", "export", "approve"]
    for action in actions:
        resp = await client.post("/audit/logs", json={**SAMPLE_LOG, "action": action})
        assert resp.status_code == 201, f"Action '{action}' failed"


@pytest.mark.anyio
async def test_search_empty_result(client: AsyncClient):
    """Search with no matches returns empty list."""
    await client.post("/audit/logs", json=SAMPLE_LOG)

    resp = await client.post("/audit/logs/search", json={
        "actor": "nonexistent@example.com",
    })
    assert resp.status_code == 200
    assert resp.json() == []
