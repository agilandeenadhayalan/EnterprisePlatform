"""
Tests for the Data Retention Service API.

Covers: policy CRUD, enforcement, stats, disabled policies, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_POLICY = {
    "name": "Bronze TTL",
    "target": "bronze/raw-gps/",
    "target_type": "minio",
    "retention_days": 30,
    "description": "Delete raw GPS data after 30 days",
    "enabled": True,
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_policy(client: AsyncClient):
    """Create a retention policy."""
    resp = await client.post("/retention/policies", json=SAMPLE_POLICY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bronze TTL"
    assert data["retention_days"] == 30
    assert data["target_type"] == "minio"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.anyio
async def test_get_policy(client: AsyncClient):
    """Get a specific retention policy."""
    create_resp = await client.post("/retention/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.get(f"/retention/policies/{policy_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Bronze TTL"


@pytest.mark.anyio
async def test_get_policy_not_found(client: AsyncClient):
    """Getting non-existent policy returns 404."""
    resp = await client.get("/retention/policies/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_policies(client: AsyncClient):
    """List all retention policies."""
    await client.post("/retention/policies", json=SAMPLE_POLICY)
    await client.post("/retention/policies", json={
        **SAMPLE_POLICY,
        "name": "ClickHouse TTL",
        "target": "ride_events",
        "target_type": "clickhouse",
        "retention_days": 90,
    })

    resp = await client.get("/retention/policies")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_update_policy(client: AsyncClient):
    """Update a retention policy."""
    create_resp = await client.post("/retention/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.patch(f"/retention/policies/{policy_id}", json={
        "retention_days": 60,
        "enabled": False,
    })
    assert resp.status_code == 200
    assert resp.json()["retention_days"] == 60
    assert resp.json()["enabled"] is False


@pytest.mark.anyio
async def test_delete_policy(client: AsyncClient):
    """Delete a retention policy."""
    create_resp = await client.post("/retention/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.delete(f"/retention/policies/{policy_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/retention/policies/{policy_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_enforce_retention(client: AsyncClient):
    """Run retention enforcement on enabled policies."""
    await client.post("/retention/policies", json=SAMPLE_POLICY)
    await client.post("/retention/policies", json={
        **SAMPLE_POLICY, "name": "Events TTL", "target": "events",
        "target_type": "clickhouse", "retention_days": 90,
    })

    resp = await client.post("/retention/enforce")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_policies_checked"] == 2
    assert data["total_records_deleted"] >= 0
    assert len(data["runs"]) == 2


@pytest.mark.anyio
async def test_enforce_skips_disabled(client: AsyncClient):
    """Enforcement skips disabled policies."""
    await client.post("/retention/policies", json={
        **SAMPLE_POLICY, "enabled": False,
    })

    resp = await client.post("/retention/enforce")
    data = resp.json()
    assert data["total_policies_checked"] == 0
    assert len(data["runs"]) == 0


@pytest.mark.anyio
async def test_retention_stats_empty(client: AsyncClient):
    """Stats on empty retention service."""
    resp = await client.get("/retention/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_policies"] == 0
    assert data["total_enforcement_runs"] == 0


@pytest.mark.anyio
async def test_retention_stats_after_enforcement(client: AsyncClient):
    """Stats reflect enforcement results."""
    await client.post("/retention/policies", json=SAMPLE_POLICY)
    await client.post("/retention/enforce")

    resp = await client.get("/retention/stats")
    data = resp.json()
    assert data["total_policies"] == 1
    assert data["enabled_policies"] == 1
    assert data["total_enforcement_runs"] == 1
    assert data["total_records_deleted"] >= 0
