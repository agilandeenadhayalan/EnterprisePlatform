"""
Tests for the Failover Manager Service API.

Covers: event CRUD, failover trigger, region promotion, health tracking,
        status reporting, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_EVENT = {
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "trigger_type": "manual",
    "reason": "Primary region degraded",
    "status": "initiated",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_event(client: AsyncClient):
    """Record a failover event."""
    resp = await client.post("/failover/events", json=SAMPLE_EVENT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_region"] == "us-east-1"
    assert data["target_region"] == "us-west-2"
    assert data["trigger_type"] == "manual"
    assert "id" in data


@pytest.mark.anyio
async def test_list_events(client: AsyncClient):
    """List failover events."""
    await client.post("/failover/events", json=SAMPLE_EVENT)
    await client.post("/failover/events", json={
        **SAMPLE_EVENT, "reason": "Scheduled maintenance",
    })

    resp = await client.get("/failover/events")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_event(client: AsyncClient):
    """Get a specific failover event."""
    create_resp = await client.post("/failover/events", json=SAMPLE_EVENT)
    event_id = create_resp.json()["id"]

    resp = await client.get(f"/failover/events/{event_id}")
    assert resp.status_code == 200
    assert resp.json()["source_region"] == "us-east-1"


@pytest.mark.anyio
async def test_get_event_not_found(client: AsyncClient):
    """Getting non-existent event returns 404."""
    resp = await client.get("/failover/events/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_trigger_failover(client: AsyncClient):
    """Trigger a failover from source to target."""
    resp = await client.post("/failover/trigger", json={
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "reason": "High error rate detected",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["source_region"] == "us-east-1"
    assert data["target_region"] == "us-west-2"
    assert data["completed_at"] is not None


@pytest.mark.anyio
async def test_trigger_failover_updates_health(client: AsyncClient):
    """Triggering failover updates region health status."""
    await client.post("/failover/trigger", json={
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "reason": "Testing",
    })

    resp = await client.get("/failover/health")
    assert resp.status_code == 200
    healths = {h["region_code"]: h for h in resp.json()}
    assert healths["us-east-1"]["status"] == "failing"
    assert healths["us-east-1"]["consecutive_failures"] >= 1
    assert healths["us-west-2"]["status"] == "healthy"


@pytest.mark.anyio
async def test_promote_region(client: AsyncClient):
    """Promote a region to primary."""
    resp = await client.post("/failover/promote/eu-west-1")
    assert resp.status_code == 200
    assert resp.json()["region_code"] == "eu-west-1"
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_promote_updates_primary(client: AsyncClient):
    """Promoting a region updates the primary designation."""
    await client.post("/failover/promote/us-east-1")
    await client.post("/failover/promote/eu-west-1")

    resp = await client.get("/failover/status")
    assert resp.status_code == 200
    statuses = {s["region_code"]: s for s in resp.json()}
    assert statuses["eu-west-1"]["is_primary"] is True
    assert statuses["us-east-1"]["is_primary"] is False


@pytest.mark.anyio
async def test_failover_status_empty(client: AsyncClient):
    """Failover status returns empty list when no regions tracked."""
    resp = await client.get("/failover/status")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_failover_status_shows_active_failovers(client: AsyncClient):
    """Failover status reports active failover count."""
    await client.post("/failover/events", json=SAMPLE_EVENT)

    resp = await client.get("/failover/status")
    assert resp.status_code == 200
    statuses = resp.json()
    assert len(statuses) >= 1


@pytest.mark.anyio
async def test_health_summary(client: AsyncClient):
    """Health summary returns all tracked regions."""
    await client.post("/failover/events", json=SAMPLE_EVENT)

    resp = await client.get("/failover/health")
    assert resp.status_code == 200
    codes = [h["region_code"] for h in resp.json()]
    assert "us-east-1" in codes
    assert "us-west-2" in codes


@pytest.mark.anyio
async def test_health_summary_empty(client: AsyncClient):
    """Health summary returns empty list when no regions tracked."""
    resp = await client.get("/failover/health")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_event_with_scheduled_trigger(client: AsyncClient):
    """Record event with scheduled trigger type."""
    resp = await client.post("/failover/events", json={
        **SAMPLE_EVENT,
        "trigger_type": "scheduled",
        "reason": "Planned maintenance window",
    })
    assert resp.status_code == 201
    assert resp.json()["trigger_type"] == "scheduled"


@pytest.mark.anyio
async def test_multiple_failovers_same_source(client: AsyncClient):
    """Multiple failovers from the same source region."""
    await client.post("/failover/trigger", json={
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "reason": "First failover",
    })
    await client.post("/failover/trigger", json={
        "source_region": "us-east-1",
        "target_region": "eu-west-1",
        "reason": "Second failover",
    })

    resp = await client.get("/failover/health")
    healths = {h["region_code"]: h for h in resp.json()}
    assert healths["us-east-1"]["consecutive_failures"] >= 2


@pytest.mark.anyio
async def test_trigger_creates_event_in_history(client: AsyncClient):
    """Triggering failover also creates an event in history."""
    await client.post("/failover/trigger", json={
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "reason": "Check history",
    })

    resp = await client.get("/failover/events")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["reason"] == "Check history"
