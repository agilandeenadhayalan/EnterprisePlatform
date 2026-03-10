"""
Tests for the Compliance Reporting Service API.

Covers: report CRUD, frameworks listing, findings, filtering, and validation.
"""

import pytest
from httpx import AsyncClient


SAMPLE_REPORT = {
    "report_type": "audit",
    "framework": "SOC2",
    "generated_by": "compliance-team",
    "period_start": "2024-01-01",
    "period_end": "2024-06-30",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_report(client: AsyncClient):
    """Create a compliance report."""
    resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["framework"] == "SOC2"
    assert data["report_type"] == "audit"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.anyio
async def test_create_report_invalid_framework(client: AsyncClient):
    """Creating report with invalid framework returns 400."""
    resp = await client.post("/compliance/reports", json={
        **SAMPLE_REPORT, "framework": "INVALID",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_report(client: AsyncClient):
    """Get a specific compliance report."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]

    resp = await client.get(f"/compliance/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["framework"] == "SOC2"


@pytest.mark.anyio
async def test_get_report_not_found(client: AsyncClient):
    """Getting non-existent report returns 404."""
    resp = await client.get("/compliance/reports/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_reports(client: AsyncClient):
    """List all compliance reports."""
    await client.post("/compliance/reports", json=SAMPLE_REPORT)
    await client.post("/compliance/reports", json={**SAMPLE_REPORT, "framework": "GDPR"})

    resp = await client.get("/compliance/reports")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_reports_filter_by_framework(client: AsyncClient):
    """Filter reports by framework."""
    await client.post("/compliance/reports", json=SAMPLE_REPORT)
    await client.post("/compliance/reports", json={**SAMPLE_REPORT, "framework": "GDPR"})

    resp = await client.get("/compliance/reports?framework=SOC2")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["framework"] == "SOC2"


@pytest.mark.anyio
async def test_list_reports_filter_by_status(client: AsyncClient):
    """Filter reports by status."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]
    await client.patch(f"/compliance/reports/{report_id}", json={"status": "approved"})
    await client.post("/compliance/reports", json=SAMPLE_REPORT)

    resp = await client.get("/compliance/reports?status=approved")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_update_report(client: AsyncClient):
    """Update a compliance report."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]

    resp = await client.patch(f"/compliance/reports/{report_id}", json={
        "status": "in_review",
        "score": 87.5,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"
    assert resp.json()["score"] == 87.5


@pytest.mark.anyio
async def test_update_report_not_found(client: AsyncClient):
    """Updating non-existent report returns 404."""
    resp = await client.patch("/compliance/reports/nonexistent", json={"status": "approved"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_report(client: AsyncClient):
    """Delete a compliance report."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]

    resp = await client.delete(f"/compliance/reports/{report_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/compliance/reports/{report_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_report_not_found(client: AsyncClient):
    """Deleting non-existent report returns 404."""
    resp = await client.delete("/compliance/reports/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_frameworks(client: AsyncClient):
    """List all supported compliance frameworks."""
    resp = await client.get("/compliance/frameworks")
    assert resp.status_code == 200
    frameworks = resp.json()
    assert len(frameworks) == 4
    names = [f["name"] for f in frameworks]
    assert "SOC2" in names
    assert "ISO27001" in names
    assert "GDPR" in names
    assert "HIPAA" in names


@pytest.mark.anyio
async def test_add_finding(client: AsyncClient):
    """Add a finding to a compliance report."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]

    resp = await client.post(f"/compliance/reports/{report_id}/findings", json={
        "category": "Access Control",
        "description": "MFA not enforced for admin accounts",
        "severity": "high",
        "remediation": "Enable MFA for all admin accounts",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "Access Control"
    assert data["severity"] == "high"
    assert "id" in data


@pytest.mark.anyio
async def test_add_finding_to_nonexistent_report(client: AsyncClient):
    """Adding finding to non-existent report returns 404."""
    resp = await client.post("/compliance/reports/nonexistent/findings", json={
        "category": "Security",
        "description": "Test finding",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_finding_appears_in_report(client: AsyncClient):
    """Finding appears in report details after adding."""
    create_resp = await client.post("/compliance/reports", json=SAMPLE_REPORT)
    report_id = create_resp.json()["id"]

    await client.post(f"/compliance/reports/{report_id}/findings", json={
        "category": "Encryption",
        "description": "Data at rest not encrypted",
        "severity": "critical",
    })

    resp = await client.get(f"/compliance/reports/{report_id}")
    assert resp.status_code == 200
    assert len(resp.json()["findings"]) == 1
    assert resp.json()["findings"][0]["severity"] == "critical"


@pytest.mark.anyio
async def test_list_reports_empty(client: AsyncClient):
    """Listing reports when none exist returns empty list."""
    resp = await client.get("/compliance/reports")
    assert resp.status_code == 200
    assert resp.json() == []
