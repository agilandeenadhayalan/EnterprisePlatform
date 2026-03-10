"""
Tests for the Conflict Resolver Service API.

Covers: conflict detection, LWW resolution, CRDT merges (counter, set, register),
        strategies listing, stats, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_DETECT = {
    "entity_id": "user-123",
    "version_a": {"name": "Alice", "email": "alice@old.com", "timestamp": "2024-01-01T10:00:00"},
    "version_b": {"name": "Alice B.", "email": "alice@new.com", "timestamp": "2024-01-01T12:00:00"},
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_detect_conflict(client: AsyncClient):
    """Detect a write-write conflict."""
    resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["conflict_type"] == "write_write"
    assert data["entity_id"] == "user-123"
    assert data["status"] == "detected"
    assert "id" in data


@pytest.mark.anyio
async def test_detect_schema_conflict(client: AsyncClient):
    """Detect a schema conflict (different keys)."""
    resp = await client.post("/conflicts/detect", json={
        "entity_id": "config-1",
        "version_a": {"name": "v1", "timestamp": "2024-01-01T10:00:00"},
        "version_b": {"name": "v2", "extra_field": "val", "timestamp": "2024-01-01T12:00:00"},
    })
    assert resp.status_code == 201
    assert resp.json()["conflict_type"] == "schema"


@pytest.mark.anyio
async def test_resolve_lww(client: AsyncClient):
    """Resolve conflict using last-writer-wins strategy."""
    detect_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = detect_resp.json()["id"]

    resp = await client.post("/conflicts/resolve", json={
        "conflict_id": conflict_id,
        "strategy": "lww",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolution_strategy"] == "lww"
    # version_b has later timestamp, so it should win
    assert data["resolved_value"]["timestamp"] == "2024-01-01T12:00:00"


@pytest.mark.anyio
async def test_resolve_manual(client: AsyncClient):
    """Resolve conflict manually."""
    detect_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = detect_resp.json()["id"]

    resp = await client.post("/conflicts/resolve", json={
        "conflict_id": conflict_id,
        "strategy": "manual",
        "manual_value": {"name": "Alice B.", "email": "alice@final.com"},
    })
    assert resp.status_code == 200
    assert resp.json()["resolved_value"]["email"] == "alice@final.com"


@pytest.mark.anyio
async def test_resolve_merge(client: AsyncClient):
    """Resolve conflict using merge strategy."""
    detect_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = detect_resp.json()["id"]

    resp = await client.post("/conflicts/resolve", json={
        "conflict_id": conflict_id,
        "strategy": "merge",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.anyio
async def test_resolve_not_found(client: AsyncClient):
    """Resolving non-existent conflict returns 404."""
    resp = await client.post("/conflicts/resolve", json={
        "conflict_id": "nonexistent",
        "strategy": "lww",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_resolve_invalid_strategy(client: AsyncClient):
    """Resolving with invalid strategy returns 400."""
    detect_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = detect_resp.json()["id"]

    resp = await client.post("/conflicts/resolve", json={
        "conflict_id": conflict_id,
        "strategy": "invalid",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_conflicts(client: AsyncClient):
    """List all conflicts."""
    await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    await client.post("/conflicts/detect", json={
        **SAMPLE_DETECT, "entity_id": "user-456",
    })

    resp = await client.get("/conflicts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_conflict(client: AsyncClient):
    """Get a specific conflict."""
    create_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = create_resp.json()["id"]

    resp = await client.get(f"/conflicts/{conflict_id}")
    assert resp.status_code == 200
    assert resp.json()["entity_id"] == "user-123"


@pytest.mark.anyio
async def test_get_conflict_not_found(client: AsyncClient):
    """Getting non-existent conflict returns 404."""
    resp = await client.get("/conflicts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_crdt_merge_counter(client: AsyncClient):
    """CRDT counter merge — take max per key."""
    resp = await client.post("/conflicts/merge", json={
        "merge_type": "counter",
        "state_a": {"node1": 5, "node2": 3},
        "state_b": {"node1": 3, "node2": 7, "node3": 2},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["merge_type"] == "counter"
    assert data["merged_state"]["node1"] == 5
    assert data["merged_state"]["node2"] == 7
    assert data["merged_state"]["node3"] == 2
    assert data["elements_merged"] == 3


@pytest.mark.anyio
async def test_crdt_merge_set(client: AsyncClient):
    """CRDT set merge — union of both sets."""
    resp = await client.post("/conflicts/merge", json={
        "merge_type": "set",
        "state_a": ["a", "b", "c"],
        "state_b": ["b", "c", "d", "e"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["merge_type"] == "set"
    assert set(data["merged_state"]) == {"a", "b", "c", "d", "e"}
    assert data["elements_merged"] == 5


@pytest.mark.anyio
async def test_crdt_merge_register(client: AsyncClient):
    """CRDT register merge — latest timestamp wins."""
    resp = await client.post("/conflicts/merge", json={
        "merge_type": "register",
        "state_a": {"value": "old", "timestamp": "2024-01-01T10:00:00"},
        "state_b": {"value": "new", "timestamp": "2024-01-01T12:00:00"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["merged_state"]["value"] == "new"
    assert data["elements_merged"] == 1


@pytest.mark.anyio
async def test_crdt_merge_invalid_type(client: AsyncClient):
    """CRDT merge with invalid type returns 400."""
    resp = await client.post("/conflicts/merge", json={
        "merge_type": "invalid",
        "state_a": {},
        "state_b": {},
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_strategies(client: AsyncClient):
    """List available resolution strategies."""
    resp = await client.get("/conflicts/strategies")
    assert resp.status_code == 200
    strategies = resp.json()
    assert len(strategies) == 4
    names = [s["name"] for s in strategies]
    assert "lww" in names
    assert "crdt" in names


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    """Get conflict resolution statistics."""
    # Create and resolve a conflict
    detect_resp = await client.post("/conflicts/detect", json=SAMPLE_DETECT)
    conflict_id = detect_resp.json()["id"]
    await client.post("/conflicts/resolve", json={
        "conflict_id": conflict_id,
        "strategy": "lww",
    })
    # Create an unresolved conflict
    await client.post("/conflicts/detect", json={
        **SAMPLE_DETECT, "entity_id": "user-789",
    })

    resp = await client.get("/conflicts/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_conflicts"] == 2
    assert data["resolved"] == 1
    assert data["pending"] == 1
    assert data["by_strategy"]["lww"] == 1
