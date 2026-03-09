"""
Tests for the Test Data Generator Service API.

Covers: start/stop generation, batch generation, templates, status,
validation, and edge cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_templates(client: AsyncClient):
    """List available event templates."""
    resp = await client.get("/generate/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    types = [t["event_type"] for t in data["templates"]]
    assert "ride" in types
    assert "location" in types
    assert "payment" in types
    assert "driver" in types


@pytest.mark.anyio
async def test_templates_have_sample_data(client: AsyncClient):
    """Event templates include sample data."""
    resp = await client.get("/generate/templates")
    for template in resp.json()["templates"]:
        assert "sample" in template
        assert len(template["sample"]) > 0
        assert "fields" in template
        assert len(template["fields"]) > 0


@pytest.mark.anyio
async def test_initial_status(client: AsyncClient):
    """Initial status shows generator is not running."""
    resp = await client.get("/generate/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_running"] is False
    assert data["events_generated"] == 0


@pytest.mark.anyio
async def test_start_generation_synthetic(client: AsyncClient):
    """Start generation in synthetic mode."""
    resp = await client.post("/generate/start", json={
        "mode": "synthetic",
        "events_per_second": 10,
        "duration_seconds": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "completed" in data["message"].lower() or "Generation" in data["message"]
    assert data["status"]["events_generated"] > 0


@pytest.mark.anyio
async def test_start_generation_replay(client: AsyncClient):
    """Start generation in replay mode."""
    resp = await client.post("/generate/start", json={
        "mode": "replay",
        "events_per_second": 5,
        "duration_seconds": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["status"]["events_generated"] > 0


@pytest.mark.anyio
async def test_start_generation_stress(client: AsyncClient):
    """Start generation in stress mode."""
    resp = await client.post("/generate/start", json={
        "mode": "stress",
        "events_per_second": 100,
        "duration_seconds": 2,
    })
    assert resp.status_code == 200
    assert resp.json()["status"]["events_generated"] > 0


@pytest.mark.anyio
async def test_start_generation_invalid_mode(client: AsyncClient):
    """Starting with invalid mode returns 400."""
    resp = await client.post("/generate/start", json={
        "mode": "invalid",
        "events_per_second": 10,
        "duration_seconds": 5,
    })
    assert resp.status_code == 400
    assert "Invalid mode" in resp.json()["detail"]


@pytest.mark.anyio
async def test_stop_generation(client: AsyncClient):
    """Stop generation returns stopped status."""
    resp = await client.post("/generate/stop")
    assert resp.status_code == 200
    assert resp.json()["status"]["is_running"] is False


@pytest.mark.anyio
async def test_batch_generate_rides(client: AsyncClient):
    """Generate a batch of ride events."""
    resp = await client.post("/generate/batch", json={
        "count": 5,
        "event_type": "ride",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 5
    assert data["event_type"] == "ride"
    for event in data["events"]:
        assert event["event_type"] == "ride"
        assert "ride_id" in event["data"]
        assert "pickup_zone_id" in event["data"]
        assert 1 <= event["data"]["pickup_zone_id"] <= 265
        assert "fare_amount" in event["data"]


@pytest.mark.anyio
async def test_batch_generate_locations(client: AsyncClient):
    """Generate a batch of location events."""
    resp = await client.post("/generate/batch", json={
        "count": 3,
        "event_type": "location",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 3
    for event in data["events"]:
        assert event["event_type"] == "location"
        assert "lat" in event["data"]
        assert "lng" in event["data"]
        assert 40.4 <= event["data"]["lat"] <= 41.0
        assert -74.3 <= event["data"]["lng"] <= -73.7


@pytest.mark.anyio
async def test_batch_generate_payments(client: AsyncClient):
    """Generate a batch of payment events."""
    resp = await client.post("/generate/batch", json={
        "count": 4,
        "event_type": "payment",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 4
    for event in data["events"]:
        assert event["event_type"] == "payment"
        assert "amount" in event["data"]
        assert "method" in event["data"]
        assert event["data"]["total"] >= event["data"]["amount"]


@pytest.mark.anyio
async def test_batch_generate_driver_events(client: AsyncClient):
    """Generate a batch of driver status events."""
    resp = await client.post("/generate/batch", json={
        "count": 3,
        "event_type": "driver",
    })
    assert resp.status_code == 201
    for event in resp.json()["events"]:
        assert "driver_id" in event["data"]
        assert "status" in event["data"]
        assert "zone_id" in event["data"]


@pytest.mark.anyio
async def test_batch_generate_invalid_type(client: AsyncClient):
    """Batch generation with invalid event type returns 400."""
    resp = await client.post("/generate/batch", json={
        "count": 5,
        "event_type": "invalid_type",
    })
    assert resp.status_code == 400
    assert "Invalid event_type" in resp.json()["detail"]


@pytest.mark.anyio
async def test_batch_generate_updates_status(client: AsyncClient):
    """Batch generation updates the events_generated counter."""
    await client.post("/generate/batch", json={
        "count": 10,
        "event_type": "ride",
    })

    resp = await client.get("/generate/status")
    assert resp.json()["events_generated"] == 10

    await client.post("/generate/batch", json={
        "count": 5,
        "event_type": "location",
    })

    resp = await client.get("/generate/status")
    assert resp.json()["events_generated"] == 15


@pytest.mark.anyio
async def test_batch_generate_count_too_large(client: AsyncClient):
    """Batch generation with count > 10000 returns 400."""
    resp = await client.post("/generate/batch", json={
        "count": 10001,
        "event_type": "ride",
    })
    assert resp.status_code == 400
    assert "must not exceed 10000" in resp.json()["detail"]
