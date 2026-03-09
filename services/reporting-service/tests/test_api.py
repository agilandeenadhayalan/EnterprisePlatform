"""
Tests for the Reporting Service API.

Covers: report generation, listing, filtering, types, deletion, validation, and edge cases.
"""

import pytest
from httpx import AsyncClient


DAILY_SUMMARY_REQUEST = {
    "report_type": "daily_summary",
    "parameters": {"date": "2024-01-15"},
    "format": "json",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_report_types(client: AsyncClient):
    """List available report types."""
    resp = await client.get("/reports/types")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    type_ids = [t["type_id"] for t in data["report_types"]]
    assert "daily_summary" in type_ids
    assert "weekly_zone_analysis" in type_ids
    assert "driver_scorecard" in type_ids
    assert "revenue_report" in type_ids
    assert "trip_patterns" in type_ids


@pytest.mark.anyio
async def test_generate_daily_summary(client: AsyncClient):
    """Generate a daily summary report."""
    resp = await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "daily_summary"
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["result"]["row_count"] > 0
    assert "total_rides" in data["result"]["summary"]


@pytest.mark.anyio
async def test_generate_driver_scorecard(client: AsyncClient):
    """Generate a driver scorecard report."""
    resp = await client.post("/reports/generate", json={
        "report_type": "driver_scorecard",
        "parameters": {"driver_id": "drv-0001"},
        "format": "json",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "driver_scorecard"
    assert data["result"]["summary"]["driver_id"] == "drv-0001"


@pytest.mark.anyio
async def test_generate_trip_patterns(client: AsyncClient):
    """Generate a trip patterns report (no required params)."""
    resp = await client.post("/reports/generate", json={
        "report_type": "trip_patterns",
        "parameters": {},
        "format": "json",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


@pytest.mark.anyio
async def test_generate_unknown_type(client: AsyncClient):
    """Generating a report with unknown type returns 400."""
    resp = await client.post("/reports/generate", json={
        "report_type": "nonexistent_report",
        "parameters": {},
    })
    assert resp.status_code == 400
    assert "Unknown report type" in resp.json()["detail"]


@pytest.mark.anyio
async def test_generate_missing_required_params(client: AsyncClient):
    """Generating a report with missing required params returns 400."""
    resp = await client.post("/reports/generate", json={
        "report_type": "daily_summary",
        "parameters": {},  # missing required "date"
    })
    assert resp.status_code == 400
    assert "Missing required parameters" in resp.json()["detail"]


@pytest.mark.anyio
async def test_generate_unsupported_format(client: AsyncClient):
    """Generating a report with unsupported format returns 400."""
    resp = await client.post("/reports/generate", json={
        "report_type": "weekly_zone_analysis",
        "parameters": {"start_date": "2024-01-15"},
        "format": "pdf",  # not supported for this type
    })
    assert resp.status_code == 400
    assert "not supported" in resp.json()["detail"]


@pytest.mark.anyio
async def test_get_report(client: AsyncClient):
    """Retrieve a generated report by ID."""
    create_resp = await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)
    report_id = create_resp.json()["id"]

    resp = await client.get(f"/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == report_id
    assert resp.json()["result"] is not None


@pytest.mark.anyio
async def test_get_report_not_found(client: AsyncClient):
    """Getting a non-existent report returns 404."""
    resp = await client.get("/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_reports_empty(client: AsyncClient):
    """Listing reports when none exist returns empty list."""
    resp = await client.get("/reports")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["reports"] == []


@pytest.mark.anyio
async def test_list_reports(client: AsyncClient):
    """List all generated reports."""
    await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)
    await client.post("/reports/generate", json={
        "report_type": "trip_patterns",
        "parameters": {},
    })

    resp = await client.get("/reports")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.anyio
async def test_list_reports_filter_by_type(client: AsyncClient):
    """Filter reports by type."""
    await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)
    await client.post("/reports/generate", json={
        "report_type": "trip_patterns",
        "parameters": {},
    })

    resp = await client.get("/reports?type=daily_summary")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["reports"][0]["report_type"] == "daily_summary"


@pytest.mark.anyio
async def test_list_reports_filter_by_status(client: AsyncClient):
    """Filter reports by status."""
    await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)

    resp = await client.get("/reports?status=completed")
    assert resp.json()["total"] == 1

    resp = await client.get("/reports?status=pending")
    assert resp.json()["total"] == 0


@pytest.mark.anyio
async def test_delete_report(client: AsyncClient):
    """Delete a report."""
    create_resp = await client.post("/reports/generate", json=DAILY_SUMMARY_REQUEST)
    report_id = create_resp.json()["id"]

    resp = await client.delete(f"/reports/{report_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/reports/{report_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_report_not_found(client: AsyncClient):
    """Deleting a non-existent report returns 404."""
    resp = await client.delete("/reports/nonexistent-id")
    assert resp.status_code == 404
