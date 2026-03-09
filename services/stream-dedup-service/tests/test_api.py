"""
Tests for the stream-dedup-service API.

Tests event deduplication, sliding window, cache management, and stats.
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


# -- POST /dedup --


@pytest.mark.anyio
async def test_dedup_all_unique(client, sample_unique_events):
    """All unique events pass through dedup."""
    resp = await client.post("/dedup", json={"events": sample_unique_events})
    assert resp.status_code == 200
    data = resp.json()
    assert data["unique_count"] == 3
    assert data["duplicate_count"] == 0
    assert data["total_checked"] == 3
    assert len(data["unique_events"]) == 3


@pytest.mark.anyio
async def test_dedup_with_duplicates(client, sample_duplicate_events):
    """Duplicate events are filtered out."""
    resp = await client.post("/dedup", json={"events": sample_duplicate_events})
    assert resp.status_code == 200
    data = resp.json()
    assert data["unique_count"] == 3
    assert data["duplicate_count"] == 2
    assert data["total_checked"] == 5
    assert "evt-001" in data["duplicate_event_ids"]
    assert "evt-002" in data["duplicate_event_ids"]


@pytest.mark.anyio
async def test_dedup_empty_batch(client):
    """Empty batch returns empty results."""
    resp = await client.post("/dedup", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["unique_count"] == 0
    assert data["duplicate_count"] == 0


@pytest.mark.anyio
async def test_dedup_across_batches(client, sample_unique_events):
    """Events are remembered across batches."""
    # First batch: all unique
    resp1 = await client.post("/dedup", json={"events": sample_unique_events})
    data1 = resp1.json()
    assert data1["unique_count"] == 3

    # Second batch with same events: all duplicates
    resp2 = await client.post("/dedup", json={"events": sample_unique_events})
    data2 = resp2.json()
    assert data2["unique_count"] == 0
    assert data2["duplicate_count"] == 3


@pytest.mark.anyio
async def test_dedup_custom_id_field(client):
    """Dedup using a custom event ID field."""
    events = [
        {"my_id": "a", "data": "first"},
        {"my_id": "b", "data": "second"},
        {"my_id": "a", "data": "dup"},
    ]
    resp = await client.post("/dedup", json={
        "events": events,
        "event_id_field": "my_id",
    })
    data = resp.json()
    assert data["unique_count"] == 2
    assert data["duplicate_count"] == 1


@pytest.mark.anyio
async def test_dedup_missing_id_field(client):
    """Events without the ID field are treated as unique."""
    events = [
        {"data": "no-id-1"},
        {"data": "no-id-2"},
    ]
    resp = await client.post("/dedup", json={"events": events})
    data = resp.json()
    assert data["unique_count"] == 2
    assert data["duplicate_count"] == 0


@pytest.mark.anyio
async def test_dedup_preserves_event_data(client):
    """Unique events are returned with their full data intact."""
    events = [{"event_id": "test-1", "payload": {"key": "value"}, "timestamp": "2024-01-01"}]
    resp = await client.post("/dedup", json={"events": events})
    data = resp.json()
    assert data["unique_events"][0]["payload"] == {"key": "value"}
    assert data["unique_events"][0]["timestamp"] == "2024-01-01"


# -- GET /dedup/stats --


@pytest.mark.anyio
async def test_stats_initial(client):
    """Stats start at zero."""
    resp = await client.get("/dedup/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_checked"] == 0
    assert data["total_unique"] == 0
    assert data["total_duplicates"] == 0
    assert data["cache_size"] == 0


@pytest.mark.anyio
async def test_stats_after_dedup(client, sample_duplicate_events):
    """Stats update after dedup processing."""
    await client.post("/dedup", json={"events": sample_duplicate_events})
    resp = await client.get("/dedup/stats")
    data = resp.json()
    assert data["total_checked"] == 5
    assert data["total_unique"] == 3
    assert data["total_duplicates"] == 2
    assert data["cache_size"] == 3
    assert data["hit_rate"] == 0.4  # 2/5
    assert data["miss_rate"] == 0.6  # 3/5


@pytest.mark.anyio
async def test_stats_hit_rate(client, sample_unique_events):
    """Hit rate calculates correctly across batches."""
    await client.post("/dedup", json={"events": sample_unique_events})
    await client.post("/dedup", json={"events": sample_unique_events})
    resp = await client.get("/dedup/stats")
    data = resp.json()
    assert data["total_checked"] == 6
    assert data["total_unique"] == 3
    assert data["total_duplicates"] == 3
    assert data["hit_rate"] == 0.5


# -- DELETE /dedup/cache --


@pytest.mark.anyio
async def test_clear_cache(client, sample_unique_events):
    """Clear cache removes all entries."""
    await client.post("/dedup", json={"events": sample_unique_events})
    resp = await client.delete("/dedup/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cleared"] == 3
    assert data["status"] == "cleared"


@pytest.mark.anyio
async def test_clear_cache_allows_reprocessing(client, sample_unique_events):
    """After clearing cache, previously seen events are unique again."""
    await client.post("/dedup", json={"events": sample_unique_events})
    await client.delete("/dedup/cache")

    resp = await client.post("/dedup", json={"events": sample_unique_events})
    data = resp.json()
    assert data["unique_count"] == 3
    assert data["duplicate_count"] == 0
