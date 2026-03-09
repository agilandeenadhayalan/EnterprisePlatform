"""
Tests for the kafka-consumer-rides API.

Tests event archiving to MinIO Bronze layer, stats, and file listing.
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
async def test_archive_batch(client, sample_ride_events):
    """Archive a batch of events successfully."""
    resp = await client.post("/archive", json={
        "events": sample_ride_events,
        "topic": "ride.events.v1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["archived"] == 2
    assert data["status"] == "archived"
    assert data["file_size"] > 0
    assert "ride.events.v1" in data["file_path"]


@pytest.mark.anyio
async def test_archive_empty_batch(client):
    """Archiving empty batch returns zero."""
    resp = await client.post("/archive", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["archived"] == 0


@pytest.mark.anyio
async def test_archive_file_path_format(client, sample_ride_events):
    """Archived file path follows year/month/day partitioning."""
    resp = await client.post("/archive", json={
        "events": sample_ride_events,
        "topic": "ride.events.v1",
    })
    data = resp.json()
    file_path = data["file_path"]
    assert "year=" in file_path
    assert "month=" in file_path
    assert "day=" in file_path
    assert file_path.endswith(".json.gz")


@pytest.mark.anyio
async def test_archive_multiple_batches(client, sample_ride_events):
    """Multiple archive calls create separate files."""
    await client.post("/archive", json={"events": sample_ride_events})
    await client.post("/archive", json={"events": sample_ride_events})
    resp = await client.get("/archive/files")
    data = resp.json()
    assert data["total"] == 2


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
async def test_stats_after_archiving(client, sample_ride_events):
    """Stats update after archiving events."""
    await client.post("/archive", json={"events": sample_ride_events})
    resp = await client.get("/archive/stats")
    data = resp.json()
    assert data["events_archived"] == 2
    assert data["files_written"] == 1
    assert data["bytes_written"] > 0
    assert data["last_archived_at"] is not None


@pytest.mark.anyio
async def test_stats_cumulative(client, sample_ride_events):
    """Stats accumulate across multiple archive operations."""
    await client.post("/archive", json={"events": sample_ride_events})
    await client.post("/archive", json={"events": [sample_ride_events[0]]})
    resp = await client.get("/archive/stats")
    data = resp.json()
    assert data["events_archived"] == 3
    assert data["files_written"] == 2


# -- GET /archive/files --


@pytest.mark.anyio
async def test_list_files_empty(client):
    """No files initially."""
    resp = await client.get("/archive/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["files"] == []


@pytest.mark.anyio
async def test_list_files_after_archiving(client, sample_ride_events):
    """Files appear after archiving."""
    await client.post("/archive", json={"events": sample_ride_events})
    resp = await client.get("/archive/files")
    data = resp.json()
    assert data["total"] == 1
    f = data["files"][0]
    assert f["event_count"] == 2
    assert f["file_size"] > 0
    assert f["topic"] == "ride.events.v1"


@pytest.mark.anyio
async def test_list_files_custom_topic(client, sample_ride_events):
    """Archive with custom topic name."""
    await client.post("/archive", json={
        "events": sample_ride_events,
        "topic": "ride.events.v2",
    })
    resp = await client.get("/archive/files")
    data = resp.json()
    assert data["files"][0]["topic"] == "ride.events.v2"
