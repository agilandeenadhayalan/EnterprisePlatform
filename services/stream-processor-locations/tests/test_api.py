"""
Tests for the stream-processor-locations API.

Tests location event processing, zone resolution, buffering, and flush.
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


# -- POST /process --


@pytest.mark.anyio
async def test_process_single_location(client, sample_location_event):
    """Process a single location event."""
    resp = await client.post("/process", json={"events": [sample_location_event]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["buffered"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1


@pytest.mark.anyio
async def test_process_batch_locations(client, sample_location_event, sample_brooklyn_event):
    """Process multiple location events."""
    resp = await client.post("/process", json={
        "events": [sample_location_event, sample_brooklyn_event]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["buffered"] == 2
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_process_empty_batch(client):
    """Empty batch returns zero results."""
    resp = await client.post("/process", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["buffered"] == 0


@pytest.mark.anyio
async def test_process_invalid_event(client):
    """Invalid events are counted as failures."""
    resp = await client.post("/process", json={"events": [{"bad": "data"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["buffered"] == 0
    assert data["failed"] == 1


# -- Zone resolution --


@pytest.mark.anyio
async def test_zone_resolution_midtown(client, sample_location_event):
    """Manhattan Midtown coordinates resolve to zone 1."""
    resp = await client.post("/process", json={"events": [sample_location_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["zone_id"] == 1
    assert result["zone_name"] == "Manhattan-Midtown"


@pytest.mark.anyio
async def test_zone_resolution_brooklyn(client, sample_brooklyn_event):
    """Brooklyn coordinates resolve to zone 4."""
    resp = await client.post("/process", json={"events": [sample_brooklyn_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["zone_id"] == 4
    assert result["zone_name"] == "Brooklyn"


@pytest.mark.anyio
async def test_zone_resolution_unknown(client):
    """Coordinates outside known zones return null zone."""
    event = {
        "event_id": "loc-999",
        "driver_id": "driver-999",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "heading": 0,
        "speed_kmh": 0,
        "accuracy_meters": 10,
        "timestamp": "2024-06-15T10:00:00",
        "status": "online",
    }
    resp = await client.post("/process", json={"events": [event]})
    data = resp.json()
    result = data["results"][0]
    assert result["zone_id"] is None
    assert result["zone_name"] is None


# -- POST /process/flush --


@pytest.mark.anyio
async def test_flush_buffer(client, sample_location_event):
    """Flush moves buffered events to flushed storage."""
    await client.post("/process", json={"events": [sample_location_event]})
    resp = await client.post("/process/flush")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flushed"] == 1
    assert data["status"] == "flushed"


@pytest.mark.anyio
async def test_flush_empty_buffer(client):
    """Flush on empty buffer returns zero."""
    resp = await client.post("/process/flush")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flushed"] == 0


# -- GET /process/stats --


@pytest.mark.anyio
async def test_stats_initial(client):
    """Stats start at zero."""
    resp = await client.get("/process/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_received"] == 0
    assert data["total_flushed"] == 0
    assert data["buffer_size"] == 0


@pytest.mark.anyio
async def test_stats_after_processing(client, sample_location_event):
    """Stats update after processing and flushing."""
    await client.post("/process", json={"events": [sample_location_event]})
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["total_received"] == 1
    assert data["buffer_size"] == 1

    await client.post("/process/flush")
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["total_flushed"] == 1
    assert data["buffer_size"] == 0
    assert data["flush_count"] == 1
