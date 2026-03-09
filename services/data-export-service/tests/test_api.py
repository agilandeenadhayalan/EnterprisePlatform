"""
Tests for the Data Export Service API.

Covers: export creation, job listing, status checking, deletion, format listing,
validation, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_EXPORT = {
    "query": "SELECT * FROM ride_events WHERE date = '2024-01-15'",
    "format": "csv",
    "destination": "download",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_export_formats(client: AsyncClient):
    """List supported export formats."""
    resp = await client.get("/export/formats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    format_ids = [f["format_id"] for f in data["formats"]]
    assert "csv" in format_ids
    assert "parquet" in format_ids
    assert "json" in format_ids
    assert "xlsx" in format_ids


@pytest.mark.anyio
async def test_start_export_csv(client: AsyncClient):
    """Start a CSV export job."""
    resp = await client.post("/export", json=SAMPLE_EXPORT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["format"] == "csv"
    assert data["status"] == "completed"
    assert data["download_url"] is not None
    assert data["row_count"] > 0
    assert data["file_size_bytes"] > 0
    assert data["download_url"].endswith(".csv")


@pytest.mark.anyio
async def test_start_export_parquet(client: AsyncClient):
    """Start a Parquet export job."""
    resp = await client.post("/export", json={
        "query": "SELECT * FROM ride_events",
        "format": "parquet",
    })
    assert resp.status_code == 201
    assert resp.json()["format"] == "parquet"
    assert resp.json()["download_url"].endswith(".parquet")


@pytest.mark.anyio
async def test_start_export_json(client: AsyncClient):
    """Start a JSON export job."""
    resp = await client.post("/export", json={
        "query": "SELECT zone_id, count(*) FROM ride_events GROUP BY zone_id",
        "format": "json",
    })
    assert resp.status_code == 201
    assert resp.json()["format"] == "json"
    assert resp.json()["download_url"].endswith(".json")


@pytest.mark.anyio
async def test_start_export_invalid_format(client: AsyncClient):
    """Starting an export with unsupported format returns 400."""
    resp = await client.post("/export", json={
        "query": "SELECT * FROM rides",
        "format": "yaml",
    })
    assert resp.status_code == 400
    assert "Unsupported format" in resp.json()["detail"]


@pytest.mark.anyio
async def test_start_export_empty_query(client: AsyncClient):
    """Starting an export with empty query returns 400."""
    resp = await client.post("/export", json={
        "query": "   ",
        "format": "csv",
    })
    assert resp.status_code == 400
    assert "Query must not be empty" in resp.json()["detail"]


@pytest.mark.anyio
async def test_get_export_job(client: AsyncClient):
    """Retrieve an export job by ID."""
    create_resp = await client.post("/export", json=SAMPLE_EXPORT)
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/export/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id
    assert resp.json()["download_url"] is not None


@pytest.mark.anyio
async def test_get_export_job_not_found(client: AsyncClient):
    """Getting a non-existent export job returns 404."""
    resp = await client.get("/export/jobs/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_export_jobs_empty(client: AsyncClient):
    """Listing jobs when none exist returns empty list."""
    resp = await client.get("/export/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["jobs"] == []


@pytest.mark.anyio
async def test_list_export_jobs(client: AsyncClient):
    """List all export jobs."""
    await client.post("/export", json=SAMPLE_EXPORT)
    await client.post("/export", json={
        "query": "SELECT * FROM drivers",
        "format": "json",
    })

    resp = await client.get("/export/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.anyio
async def test_delete_export_job(client: AsyncClient):
    """Delete an export job."""
    create_resp = await client.post("/export", json=SAMPLE_EXPORT)
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"/export/jobs/{job_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/export/jobs/{job_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_export_job_not_found(client: AsyncClient):
    """Deleting a non-existent export job returns 404."""
    resp = await client.delete("/export/jobs/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_export_format_details(client: AsyncClient):
    """Export formats include content type and extension info."""
    resp = await client.get("/export/formats")
    csv_format = [f for f in resp.json()["formats"] if f["format_id"] == "csv"][0]
    assert csv_format["content_type"] == "text/csv"
    assert csv_format["extension"] == ".csv"
    assert csv_format["name"] == "CSV"
