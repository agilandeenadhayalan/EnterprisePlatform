"""
Tests for the Incident Service API.

Covers: incident CRUD, investigation, resolution, notes, stats, filtering, validation.
"""

import pytest
from httpx import AsyncClient


SAMPLE_INCIDENT = {
    "type": "accident",
    "severity": "high",
    "reported_by": "driver-001",
    "description": "Minor collision at intersection of Main St and 5th Ave",
    "location": {"lat": 40.7128, "lng": -74.0060, "address": "Main St & 5th Ave"},
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_incident(client: AsyncClient):
    """Report a new incident."""
    resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "accident"
    assert data["severity"] == "high"
    assert data["status"] == "reported"
    assert "id" in data


@pytest.mark.anyio
async def test_create_incident_invalid_severity(client: AsyncClient):
    """Creating incident with invalid severity returns 400."""
    resp = await client.post("/incidents", json={
        **SAMPLE_INCIDENT, "severity": "extreme",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_incident(client: AsyncClient):
    """Get a specific incident."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    resp = await client.get(f"/incidents/{incident_id}")
    assert resp.status_code == 200
    assert resp.json()["type"] == "accident"


@pytest.mark.anyio
async def test_get_incident_not_found(client: AsyncClient):
    """Getting non-existent incident returns 404."""
    resp = await client.get("/incidents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_incidents(client: AsyncClient):
    """List all incidents."""
    await client.post("/incidents", json=SAMPLE_INCIDENT)
    await client.post("/incidents", json={**SAMPLE_INCIDENT, "severity": "low"})

    resp = await client.get("/incidents")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_incidents_filter_by_severity(client: AsyncClient):
    """Filter incidents by severity."""
    await client.post("/incidents", json=SAMPLE_INCIDENT)
    await client.post("/incidents", json={**SAMPLE_INCIDENT, "severity": "low"})

    resp = await client.get("/incidents?severity=high")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["severity"] == "high"


@pytest.mark.anyio
async def test_list_incidents_filter_by_status(client: AsyncClient):
    """Filter incidents by status."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]
    await client.post(f"/incidents/{incident_id}/investigate")
    await client.post("/incidents", json=SAMPLE_INCIDENT)

    resp = await client.get("/incidents?status=investigating")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_update_incident(client: AsyncClient):
    """Update an incident."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    resp = await client.patch(f"/incidents/{incident_id}", json={
        "description": "Updated description with more details",
    })
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description with more details"


@pytest.mark.anyio
async def test_update_incident_not_found(client: AsyncClient):
    """Updating non-existent incident returns 404."""
    resp = await client.patch("/incidents/nonexistent", json={"description": "test"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_investigate_incident(client: AsyncClient):
    """Begin investigation on an incident."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    resp = await client.post(f"/incidents/{incident_id}/investigate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "investigating"


@pytest.mark.anyio
async def test_investigate_not_found(client: AsyncClient):
    """Investigating non-existent incident returns 404."""
    resp = await client.post("/incidents/nonexistent/investigate")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_resolve_incident(client: AsyncClient):
    """Resolve an incident."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    resp = await client.post(f"/incidents/{incident_id}/resolve", json={
        "resolution": "Both parties exchanged information. No injuries reported.",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolved_at"] is not None
    assert resp.json()["resolution"] is not None


@pytest.mark.anyio
async def test_resolve_not_found(client: AsyncClient):
    """Resolving non-existent incident returns 404."""
    resp = await client.post("/incidents/nonexistent/resolve", json={"resolution": "test"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_add_note(client: AsyncClient):
    """Add an investigation note to an incident."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    resp = await client.post(f"/incidents/{incident_id}/notes", json={
        "author": "investigator-001",
        "content": "Reviewed dashcam footage, confirmed minor collision",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["author"] == "investigator-001"
    assert "added_at" in data


@pytest.mark.anyio
async def test_add_note_not_found(client: AsyncClient):
    """Adding note to non-existent incident returns 404."""
    resp = await client.post("/incidents/nonexistent/notes", json={
        "author": "test",
        "content": "test",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_incident_stats(client: AsyncClient):
    """Get incident statistics."""
    await client.post("/incidents", json=SAMPLE_INCIDENT)
    await client.post("/incidents", json={**SAMPLE_INCIDENT, "severity": "critical"})

    resp = await client.get("/incidents/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert "high" in data["by_severity"]
    assert "critical" in data["by_severity"]
    assert "reported" in data["by_status"]


@pytest.mark.anyio
async def test_notes_appear_in_incident(client: AsyncClient):
    """Notes appear in incident details after adding."""
    create_resp = await client.post("/incidents", json=SAMPLE_INCIDENT)
    incident_id = create_resp.json()["id"]

    await client.post(f"/incidents/{incident_id}/notes", json={
        "author": "investigator",
        "content": "Initial assessment complete",
    })

    resp = await client.get(f"/incidents/{incident_id}")
    assert resp.status_code == 200
    assert len(resp.json()["investigation_notes"]) == 1
