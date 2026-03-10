"""
Tests for the Emergency Service API.

Covers: SOS alerts, dispatch, resolve, responders, validation, edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_SOS = {
    "emergency_type": "accident",
    "reporter_id": "rider-001",
    "location": {"lat": 40.7128, "lng": -74.0060},
    "description": "Vehicle collision at intersection",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_trigger_sos(client: AsyncClient):
    """Trigger an SOS alert."""
    resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["emergency_type"] == "accident"
    assert data["status"] == "triggered"
    assert data["reporter_id"] == "rider-001"
    assert "id" in data


@pytest.mark.anyio
async def test_trigger_sos_invalid_type(client: AsyncClient):
    """Triggering SOS with invalid type returns 400."""
    resp = await client.post("/emergency/sos", json={
        **SAMPLE_SOS, "emergency_type": "earthquake",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_alert(client: AsyncClient):
    """Get an emergency alert."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]

    resp = await client.get(f"/emergency/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.json()["emergency_type"] == "accident"


@pytest.mark.anyio
async def test_get_alert_not_found(client: AsyncClient):
    """Getting non-existent alert returns 404."""
    resp = await client.get("/emergency/alerts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_active_alerts(client: AsyncClient):
    """List active emergency alerts."""
    await client.post("/emergency/sos", json=SAMPLE_SOS)
    await client.post("/emergency/sos", json={
        **SAMPLE_SOS, "emergency_type": "medical",
    })

    resp = await client.get("/emergency/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_acknowledge_alert(client: AsyncClient):
    """Acknowledge an emergency alert."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]

    resp = await client.patch(f"/emergency/alerts/{alert_id}", json={
        "status": "acknowledged",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


@pytest.mark.anyio
async def test_update_alert_not_found(client: AsyncClient):
    """Updating non-existent alert returns 404."""
    resp = await client.patch("/emergency/alerts/nonexistent", json={"status": "acknowledged"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_dispatch_responder(client: AsyncClient):
    """Dispatch a responder to an alert."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]

    resp = await client.post(f"/emergency/alerts/{alert_id}/dispatch", json={
        "responder_id": "resp-001",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "dispatched"
    assert resp.json()["dispatched_responder"] == "resp-001"


@pytest.mark.anyio
async def test_dispatch_not_found(client: AsyncClient):
    """Dispatching to non-existent alert returns 404."""
    resp = await client.post("/emergency/alerts/nonexistent/dispatch", json={
        "responder_id": "resp-001",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_resolve_alert(client: AsyncClient):
    """Resolve an emergency alert."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]

    resp = await client.post(f"/emergency/alerts/{alert_id}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolved_at"] is not None


@pytest.mark.anyio
async def test_resolve_not_found(client: AsyncClient):
    """Resolving non-existent alert returns 404."""
    resp = await client.post("/emergency/alerts/nonexistent/resolve")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_resolved_alert_not_in_active_list(client: AsyncClient):
    """Resolved alerts are excluded from active alerts list."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]
    await client.post(f"/emergency/alerts/{alert_id}/resolve")

    resp = await client.get("/emergency/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_list_responders(client: AsyncClient):
    """List available emergency responders."""
    resp = await client.get("/emergency/responders")
    assert resp.status_code == 200
    responders = resp.json()
    assert len(responders) == 4
    assert any(r["name"] == "Unit Alpha" for r in responders)


@pytest.mark.anyio
async def test_responder_status_after_dispatch(client: AsyncClient):
    """Responder status changes to dispatched after dispatch."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]
    await client.post(f"/emergency/alerts/{alert_id}/dispatch", json={
        "responder_id": "resp-001",
    })

    resp = await client.get("/emergency/responders")
    responders = resp.json()
    alpha = next(r for r in responders if r["id"] == "resp-001")
    assert alpha["status"] == "dispatched"


@pytest.mark.anyio
async def test_responder_freed_after_resolve(client: AsyncClient):
    """Responder becomes available again after alert is resolved."""
    create_resp = await client.post("/emergency/sos", json=SAMPLE_SOS)
    alert_id = create_resp.json()["id"]
    await client.post(f"/emergency/alerts/{alert_id}/dispatch", json={
        "responder_id": "resp-002",
    })
    await client.post(f"/emergency/alerts/{alert_id}/resolve")

    resp = await client.get("/emergency/responders")
    responders = resp.json()
    ambulance = next(r for r in responders if r["id"] == "resp-002")
    assert ambulance["status"] == "available"
