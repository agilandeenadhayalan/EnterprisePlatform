"""
Tests for the stream-processor-rides API.

Tests ride event processing, field derivation, stats tracking, and replay.
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
    data = resp.json()
    assert data["status"] == "healthy"


# -- POST /process --


@pytest.mark.anyio
async def test_process_single_ride(client, sample_ride_event):
    """Process a single ride event successfully."""
    resp = await client.post("/process", json={"events": [sample_ride_event]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1


@pytest.mark.anyio
async def test_process_batch_rides(client, sample_ride_event, sample_weekend_event):
    """Process a batch of multiple ride events."""
    resp = await client.post("/process", json={
        "events": [sample_ride_event, sample_weekend_event]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 2
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_process_empty_batch(client):
    """Process an empty batch returns zero results."""
    resp = await client.post("/process", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["failed"] == 0
    assert data["results"] == []


@pytest.mark.anyio
async def test_process_invalid_event(client):
    """Invalid events increment failure count."""
    resp = await client.post("/process", json={"events": [{"bad": "data"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["failed"] == 1


@pytest.mark.anyio
async def test_process_mixed_valid_invalid(client, sample_ride_event):
    """Batch with mixed valid and invalid events processes valid ones."""
    resp = await client.post("/process", json={
        "events": [sample_ride_event, {"invalid": True}, sample_ride_event]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 2
    assert data["failed"] == 1


# -- Field derivation --


@pytest.mark.anyio
async def test_trip_duration_calculation(client, sample_ride_event):
    """Trip duration is calculated correctly from pickup/dropoff times."""
    resp = await client.post("/process", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    # 08:30 to 08:55 = 25 minutes
    assert result["trip_duration_minutes"] == 25.0


@pytest.mark.anyio
async def test_speed_calculation(client, sample_ride_event):
    """Speed is calculated from distance and duration."""
    resp = await client.post("/process", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    # 3.2 miles / (25 min / 60) = 3.2 / 0.4167 = 7.68 mph
    assert result["speed_mph"] > 0
    expected_speed = round(3.2 / (25.0 / 60.0), 2)
    assert result["speed_mph"] == expected_speed


@pytest.mark.anyio
async def test_total_amount_calculation(client, sample_ride_event):
    """Total amount = fare + tip."""
    resp = await client.post("/process", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["total_amount"] == 30.50  # 25.50 + 5.00


@pytest.mark.anyio
async def test_pickup_hour_derivation(client, sample_ride_event):
    """Pickup hour is extracted from pickup time."""
    resp = await client.post("/process", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["pickup_hour"] == 8  # 08:30


@pytest.mark.anyio
async def test_weekend_detection_weekday(client, sample_ride_event):
    """Weekday ride is not flagged as weekend."""
    # June 15, 2024 is a Saturday, but let's use a known weekday
    event = sample_ride_event.copy()
    event["pickup_at"] = "2024-06-17T08:30:00"  # Monday
    event["dropoff_at"] = "2024-06-17T08:55:00"
    resp = await client.post("/process", json={"events": [event]})
    data = resp.json()
    result = data["results"][0]
    assert result["is_weekend"] is False
    assert result["pickup_day_of_week"] == 0  # Monday


@pytest.mark.anyio
async def test_weekend_detection_saturday(client, sample_ride_event):
    """Saturday ride is flagged as weekend."""
    event = sample_ride_event.copy()
    event["pickup_at"] = "2024-06-15T22:00:00"  # Saturday
    event["dropoff_at"] = "2024-06-15T22:20:00"
    resp = await client.post("/process", json={"events": [event]})
    data = resp.json()
    result = data["results"][0]
    assert result["is_weekend"] is True
    assert result["pickup_day_of_week"] == 5  # Saturday


# -- GET /process/stats --


@pytest.mark.anyio
async def test_stats_initial(client):
    """Stats start at zero."""
    resp = await client.get("/process/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events_processed"] == 0
    assert data["events_failed"] == 0
    assert data["error_count"] == 0


@pytest.mark.anyio
async def test_stats_after_processing(client, sample_ride_event):
    """Stats update after processing events."""
    await client.post("/process", json={"events": [sample_ride_event]})
    resp = await client.get("/process/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events_processed"] == 1
    assert data["last_processed_at"] is not None


@pytest.mark.anyio
async def test_stats_error_tracking(client):
    """Error count increments for failed events."""
    await client.post("/process", json={"events": [{"bad": "event"}]})
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["error_count"] == 1
    assert data["events_failed"] == 1


# -- POST /process/replay --


@pytest.mark.anyio
async def test_replay_events(client, sample_ride_event):
    """Replay returns rides in the specified time range."""
    await client.post("/process", json={"events": [sample_ride_event]})
    resp = await client.post("/process/replay", json={
        "start_time": "2024-06-15T00:00:00",
        "end_time": "2024-06-15T23:59:59",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["replayed_count"] >= 1


@pytest.mark.anyio
async def test_replay_no_match(client, sample_ride_event):
    """Replay with out-of-range times returns zero."""
    await client.post("/process", json={"events": [sample_ride_event]})
    resp = await client.post("/process/replay", json={
        "start_time": "2025-01-01T00:00:00",
        "end_time": "2025-01-02T00:00:00",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["replayed_count"] == 0
