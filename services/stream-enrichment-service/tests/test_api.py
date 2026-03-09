"""
Tests for the stream-enrichment-service API.

Tests event enrichment with zone names, weather data, dimension cache, and refresh.
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


# -- POST /enrich --


@pytest.mark.anyio
async def test_enrich_ride_event(client, sample_ride_event):
    """Enrich a ride event with zone names and weather."""
    resp = await client.post("/enrich", json={"events": [sample_ride_event]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["enriched"] == 1
    assert data["failed"] == 0
    result = data["results"][0]
    assert result["pickup_zone_name"] == "Midtown Center"
    assert result["pickup_borough"] == "Manhattan"
    assert result["dropoff_zone_name"] == "Upper East Side South"
    assert result["dropoff_borough"] == "Manhattan"


@pytest.mark.anyio
async def test_enrich_with_weather(client, sample_ride_event):
    """Enrichment includes weather data from timestamp."""
    resp = await client.post("/enrich", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    # 2024-06-15T08:30 -> hour 08 -> clear, 72F
    assert result["weather_condition"] == "clear"
    assert result["temperature_f"] == 72.0
    assert result["precipitation"] is False


@pytest.mark.anyio
async def test_enrich_rainy_weather(client, sample_event_rainy):
    """Events during rain get precipitation flag."""
    resp = await client.post("/enrich", json={"events": [sample_event_rainy]})
    data = resp.json()
    result = data["results"][0]
    # 2024-06-15T14:30 -> hour 14 -> rain
    assert result["weather_condition"] == "rain"
    assert result["precipitation"] is True


@pytest.mark.anyio
async def test_enrich_no_zones(client, sample_event_no_zones):
    """Events without zone IDs get null zone enrichment."""
    resp = await client.post("/enrich", json={"events": [sample_event_no_zones]})
    data = resp.json()
    result = data["results"][0]
    assert result["pickup_zone_name"] is None
    assert result["dropoff_zone_name"] is None


@pytest.mark.anyio
async def test_enrich_unknown_zone(client):
    """Events with unknown zone IDs get null zone names."""
    event = {
        "event_id": "evt-999",
        "event_type": "ride",
        "pickup_zone_id": 9999,
        "dropoff_zone_id": 9998,
        "timestamp": "2024-06-15T08:30:00",
        "payload": {},
    }
    resp = await client.post("/enrich", json={"events": [event]})
    data = resp.json()
    result = data["results"][0]
    assert result["pickup_zone_name"] is None
    assert result["dropoff_zone_name"] is None


@pytest.mark.anyio
async def test_enrich_batch(client, sample_ride_event, sample_event_rainy):
    """Enrich a batch of multiple events."""
    resp = await client.post("/enrich", json={
        "events": [sample_ride_event, sample_event_rainy]
    })
    data = resp.json()
    assert data["enriched"] == 2
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_enrich_invalid_event(client):
    """Invalid events are counted as failures."""
    resp = await client.post("/enrich", json={"events": [{"bad": "data"}]})
    data = resp.json()
    assert data["enriched"] == 0
    assert data["failed"] == 1


@pytest.mark.anyio
async def test_enrich_preserves_payload(client, sample_ride_event):
    """Enrichment preserves the original event payload."""
    resp = await client.post("/enrich", json={"events": [sample_ride_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["payload"]["ride_id"] == "ride-001"
    assert result["payload"]["fare_amount"] == 25.50


@pytest.mark.anyio
async def test_enrich_empty_batch(client):
    """Empty batch returns zero results."""
    resp = await client.post("/enrich", json={"events": []})
    data = resp.json()
    assert data["enriched"] == 0


# -- GET /dimensions --


@pytest.mark.anyio
async def test_dimensions_loaded(client):
    """Dimension cache is loaded with zones and weather."""
    resp = await client.get("/dimensions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_count"] > 0
    assert data["weather_count"] > 0
    assert data["last_refreshed_at"] is not None


@pytest.mark.anyio
async def test_dimensions_zone_data(client):
    """Zone dimension data contains expected entries."""
    resp = await client.get("/dimensions")
    data = resp.json()
    # Zone 161 = Midtown Center
    assert "161" in data["zones"]
    assert data["zones"]["161"]["name"] == "Midtown Center"


# -- POST /dimensions/refresh --


@pytest.mark.anyio
async def test_refresh_dimensions(client):
    """Refresh reloads dimension caches."""
    resp = await client.post("/dimensions/refresh")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zones_loaded"] > 0
    assert data["weather_loaded"] > 0
    assert data["status"] == "refreshed"
