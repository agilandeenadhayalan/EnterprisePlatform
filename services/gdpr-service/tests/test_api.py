"""
Tests for the GDPR Service API.

Covers: DSR CRUD, processing, audit trail, consent management, filtering, validation.
"""

import pytest
from httpx import AsyncClient


SAMPLE_DSR = {
    "request_type": "access",
    "subject_email": "user@example.com",
    "data_categories": ["profile", "trip_history", "payment"],
    "notes": "User wants full data export",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_dsr(client: AsyncClient):
    """Submit a data subject request."""
    resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    assert resp.status_code == 201
    data = resp.json()
    assert data["request_type"] == "access"
    assert data["subject_email"] == "user@example.com"
    assert data["status"] == "pending"
    assert "id" in data
    assert data["due_date"] is not None


@pytest.mark.anyio
async def test_create_dsr_invalid_type(client: AsyncClient):
    """Submitting DSR with invalid type returns 400."""
    resp = await client.post("/gdpr/requests", json={
        **SAMPLE_DSR, "request_type": "invalid_type",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_dsr(client: AsyncClient):
    """Get a specific data subject request."""
    create_resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    request_id = create_resp.json()["id"]

    resp = await client.get(f"/gdpr/requests/{request_id}")
    assert resp.status_code == 200
    assert resp.json()["subject_email"] == "user@example.com"


@pytest.mark.anyio
async def test_get_dsr_not_found(client: AsyncClient):
    """Getting non-existent DSR returns 404."""
    resp = await client.get("/gdpr/requests/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_dsrs(client: AsyncClient):
    """List all data subject requests."""
    await client.post("/gdpr/requests", json=SAMPLE_DSR)
    await client.post("/gdpr/requests", json={**SAMPLE_DSR, "request_type": "erasure"})

    resp = await client.get("/gdpr/requests")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_dsrs_filter_by_type(client: AsyncClient):
    """Filter DSRs by request type."""
    await client.post("/gdpr/requests", json=SAMPLE_DSR)
    await client.post("/gdpr/requests", json={**SAMPLE_DSR, "request_type": "erasure"})

    resp = await client.get("/gdpr/requests?request_type=erasure")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["request_type"] == "erasure"


@pytest.mark.anyio
async def test_list_dsrs_filter_by_status(client: AsyncClient):
    """Filter DSRs by status."""
    create_resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    request_id = create_resp.json()["id"]
    await client.post(f"/gdpr/requests/{request_id}/process")
    await client.post("/gdpr/requests", json=SAMPLE_DSR)

    resp = await client.get("/gdpr/requests?status=completed")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_update_dsr(client: AsyncClient):
    """Update a data subject request."""
    create_resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    request_id = create_resp.json()["id"]

    resp = await client.patch(f"/gdpr/requests/{request_id}", json={
        "status": "processing",
        "notes": "Started processing",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"
    assert resp.json()["notes"] == "Started processing"


@pytest.mark.anyio
async def test_update_dsr_not_found(client: AsyncClient):
    """Updating non-existent DSR returns 404."""
    resp = await client.patch("/gdpr/requests/nonexistent", json={"status": "completed"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_process_dsr(client: AsyncClient):
    """Process a data subject request."""
    create_resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    request_id = create_resp.json()["id"]

    resp = await client.post(f"/gdpr/requests/{request_id}/process")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None


@pytest.mark.anyio
async def test_process_dsr_not_found(client: AsyncClient):
    """Processing non-existent DSR returns 404."""
    resp = await client.post("/gdpr/requests/nonexistent/process")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_audit_trail(client: AsyncClient):
    """Get audit trail for a DSR."""
    create_resp = await client.post("/gdpr/requests", json=SAMPLE_DSR)
    request_id = create_resp.json()["id"]
    await client.post(f"/gdpr/requests/{request_id}/process")

    resp = await client.get(f"/gdpr/requests/{request_id}/audit-trail")
    assert resp.status_code == 200
    trail = resp.json()
    assert len(trail) >= 2  # created + processing + completed


@pytest.mark.anyio
async def test_audit_trail_not_found(client: AsyncClient):
    """Getting audit trail for non-existent DSR returns 404."""
    resp = await client.get("/gdpr/requests/nonexistent/audit-trail")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_consent(client: AsyncClient):
    """Record a consent grant."""
    resp = await client.post("/gdpr/consent", json={
        "subject_email": "user@example.com",
        "purpose": "marketing",
        "granted": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject_email"] == "user@example.com"
    assert data["purpose"] == "marketing"
    assert data["granted"] is True


@pytest.mark.anyio
async def test_get_consent_records(client: AsyncClient):
    """Get consent records for a data subject."""
    await client.post("/gdpr/consent", json={
        "subject_email": "user@example.com",
        "purpose": "marketing",
        "granted": True,
    })
    await client.post("/gdpr/consent", json={
        "subject_email": "user@example.com",
        "purpose": "analytics",
        "granted": False,
    })

    resp = await client.get("/gdpr/consent/user@example.com")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 2


@pytest.mark.anyio
async def test_get_consent_records_empty(client: AsyncClient):
    """Get consent records for unknown subject returns empty list."""
    resp = await client.get("/gdpr/consent/unknown@example.com")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_consent_withdrawal(client: AsyncClient):
    """Record a consent withdrawal."""
    resp = await client.post("/gdpr/consent", json={
        "subject_email": "user@example.com",
        "purpose": "marketing",
        "granted": False,
    })
    assert resp.status_code == 201
    assert resp.json()["granted"] is False
