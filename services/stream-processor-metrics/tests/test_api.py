"""
Tests for the stream-processor-metrics API.

Tests metric event processing, tumbling window aggregation, flush, and stats.
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
async def test_process_single_metric(client, sample_metric_event):
    """Process a single metric event."""
    resp = await client.post("/process", json={"events": [sample_metric_event]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["failed"] == 0
    assert data["windows_updated"] == 1


@pytest.mark.anyio
async def test_process_batch_same_window(client, sample_metric_events_same_window):
    """Events in the same window update a single window."""
    resp = await client.post("/process", json={"events": sample_metric_events_same_window})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 3
    assert data["windows_updated"] == 1


@pytest.mark.anyio
async def test_process_batch_different_windows(client, sample_metric_events_different_windows):
    """Events in different windows create separate windows."""
    resp = await client.post("/process", json={"events": sample_metric_events_different_windows})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["windows_updated"] == 2


@pytest.mark.anyio
async def test_process_empty_batch(client):
    """Empty batch processes zero events."""
    resp = await client.post("/process", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 0
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_process_invalid_event(client):
    """Invalid events are counted as failures."""
    resp = await client.post("/process", json={"events": [{"bad": "data"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 0
    assert data["failed"] == 1


@pytest.mark.anyio
async def test_process_mixed_valid_invalid(client, sample_metric_event):
    """Batch with mixed valid and invalid events."""
    resp = await client.post("/process", json={
        "events": [sample_metric_event, {"invalid": True}]
    })
    data = resp.json()
    assert data["accepted"] == 1
    assert data["failed"] == 1


# -- GET /windows --


@pytest.mark.anyio
async def test_windows_empty(client):
    """No active windows initially."""
    resp = await client.get("/windows")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["active_windows"] == []


@pytest.mark.anyio
async def test_windows_after_processing(client, sample_metric_event):
    """Active windows appear after processing."""
    await client.post("/process", json={"events": [sample_metric_event]})
    resp = await client.get("/windows")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    window = data["active_windows"][0]
    assert window["metric_name"] == "ride_fare"
    assert window["event_count"] == 1
    assert window["is_open"] is True


@pytest.mark.anyio
async def test_window_aggregation_values(client, sample_metric_events_same_window):
    """Window correctly aggregates count, sum, min, max."""
    await client.post("/process", json={"events": sample_metric_events_same_window})
    resp = await client.get("/windows")
    data = resp.json()
    window = data["active_windows"][0]
    assert window["event_count"] == 3
    assert window["current_sum"] == 85.5  # 25.50 + 18.00 + 42.00
    assert window["current_min"] == 18.0
    assert window["current_max"] == 42.0


# -- POST /windows/flush --


@pytest.mark.anyio
async def test_flush_windows(client, sample_metric_events_same_window):
    """Flushing closes windows and returns aggregates."""
    await client.post("/process", json={"events": sample_metric_events_same_window})
    resp = await client.post("/windows/flush")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flushed"] == 1
    agg = data["aggregates"][0]
    assert agg["count"] == 3
    assert agg["sum_value"] == 85.5
    assert agg["avg_value"] == 28.5  # 85.5 / 3
    assert agg["min_value"] == 18.0
    assert agg["max_value"] == 42.0


@pytest.mark.anyio
async def test_flush_clears_active_windows(client, sample_metric_event):
    """After flush, no active windows remain."""
    await client.post("/process", json={"events": [sample_metric_event]})
    await client.post("/windows/flush")
    resp = await client.get("/windows")
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.anyio
async def test_flush_empty(client):
    """Flushing with no windows returns zero."""
    resp = await client.post("/windows/flush")
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
    assert data["events_processed"] == 0
    assert data["windows_created"] == 0


@pytest.mark.anyio
async def test_stats_after_processing(client, sample_metric_events_same_window):
    """Stats update after processing events."""
    await client.post("/process", json={"events": sample_metric_events_same_window})
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["events_processed"] == 3
    assert data["windows_created"] == 1
    assert data["active_window_count"] == 1


@pytest.mark.anyio
async def test_stats_after_flush(client, sample_metric_event):
    """Stats update after flushing windows."""
    await client.post("/process", json={"events": [sample_metric_event]})
    await client.post("/windows/flush")
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["windows_flushed"] == 1
    assert data["active_window_count"] == 0
