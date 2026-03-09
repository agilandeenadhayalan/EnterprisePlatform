"""
Tests for the kafka-consumer-locations API.

Tests location event archiving to MinIO Bronze layer, stats, and file listing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -- Health check --


@pytest.mark.anyio
async def test_health_check(client):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# -- POST /archive --


@pytest.mark.anyio
async def test_archive_batch(client, sample_location_events):
    """Archive a batch of location events successfully."""
    resp = await client.post("/archive", json={
        "events": sample_location_events,
        "topic": "location.events.v1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["archived"] == 3
    assert data["status"] == "archived"
    assert data["file_size"] > 0


@pytest.mark.anyio
async def test_archive_empty_batch(client):
    """Archiving empty batch returns zero."""
    resp = await client.post("/archive", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["archived"] == 0


@pytest.mark.anyio
async def test_archive_file_path_partitioned(client, sample_location_events):
    """Archived file path follows year/month/day partitioning."""
    resp = await client.post("/archive", json={"events": sample_location_events})
    data = resp.json()
    file_path = data["file_path"]
    assert "year=" in file_path
    assert "month=" in file_path
    assert "day=" in file_path
    assert file_path.endswith(".json.gz")


# -- GET /archive/stats --


@pytest.mark.anyio
async def test_stats_initial(client):
    """Stats start at zero."""
    resp = await client.get("/archive/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events_archived"] == 0
    assert data["files_written"] == 0


@pytest.mark.anyio
async def test_stats_after_archiving(client, sample_location_events):
    """Stats update after archiving events."""
    await client.post("/archive", json={"events": sample_location_events})
    resp = await client.get("/archive/stats")
    data = resp.json()
    assert data["events_archived"] == 3
    assert data["files_written"] == 1
    assert data["bytes_written"] > 0


# -- GET /archive/files --


@pytest.mark.anyio
async def test_list_files_empty(client):
    """No files initially."""
    resp = await client.get("/archive/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.anyio
async def test_list_files_after_archiving(client, sample_location_events):
    """Files appear after archiving."""
    await client.post("/archive", json={"events": sample_location_events})
    resp = await client.get("/archive/files")
    data = resp.json()
    assert data["total"] == 1
    assert data["files"][0]["event_count"] == 3
    assert data["files"][0]["topic"] == "location.events.v1"
