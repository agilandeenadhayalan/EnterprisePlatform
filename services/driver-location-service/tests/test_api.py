"""
Tests for the driver location service API.

Pure unit tests — mock the repository layer, no DB needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime


@pytest.fixture
def mock_location():
    """Mock location ORM object."""
    loc = MagicMock()
    loc.id = "aaa00000-0000-0000-0000-000000000001"
    loc.driver_id = "ddd00000-0000-0000-0000-000000000001"
    loc.latitude = 40.7128
    loc.longitude = -74.0060
    loc.heading = 90.0
    loc.speed = 30.5
    loc.accuracy = 5.0
    loc.source = "gps"
    loc.recorded_at = datetime(2024, 6, 15, 10, 30, 0)
    loc.created_at = datetime(2024, 6, 15, 10, 30, 0)
    return loc


@pytest.fixture
def mock_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.send_event = AsyncMock(return_value=True)
    return producer


@pytest.fixture
def app(mock_producer):
    """Create test app with mocked dependencies."""
    from main import app as _app
    from mobility_common.fastapi.database import get_db

    async def mock_get_db():
        yield AsyncMock()

    _app.dependency_overrides[get_db] = mock_get_db
    _app.state.producer = mock_producer
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# -- Health check --

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# -- POST /locations --

@pytest.mark.asyncio
async def test_update_location_success(client, mock_location):
    """Successfully record a location update."""
    with patch("repository.LocationRepository.create_location", new_callable=AsyncMock, return_value=mock_location):
        resp = await client.post("/locations", json={
            "driver_id": "ddd00000-0000-0000-0000-000000000001",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "heading": 90.0,
            "speed": 30.5,
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["latitude"] == 40.7128


@pytest.mark.asyncio
async def test_update_location_publishes_event(client, mock_location, mock_producer):
    """Location update publishes a Kafka event."""
    with patch("repository.LocationRepository.create_location", new_callable=AsyncMock, return_value=mock_location):
        await client.post("/locations", json={
            "driver_id": "ddd00000-0000-0000-0000-000000000001",
            "latitude": 40.7128,
            "longitude": -74.0060,
        })
    mock_producer.send_event.assert_called_once()


@pytest.mark.asyncio
async def test_update_location_invalid_latitude(client):
    """Reject latitude outside valid range."""
    resp = await client.post("/locations", json={
        "driver_id": "ddd00000-0000-0000-0000-000000000001",
        "latitude": 100.0,
        "longitude": -74.0060,
    })
    assert resp.status_code == 422


# -- GET /drivers/{id}/location --

@pytest.mark.asyncio
async def test_get_latest_location_success(client, mock_location):
    """Get latest location returns most recent record."""
    with patch("repository.LocationRepository.get_latest_location", new_callable=AsyncMock, return_value=mock_location):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/location")
    assert resp.status_code == 200
    data = resp.json()
    assert data["driver_id"] == "ddd00000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_get_latest_location_not_found(client):
    """Get latest location returns 404 when no location exists."""
    with patch("repository.LocationRepository.get_latest_location", new_callable=AsyncMock, return_value=None):
        resp = await client.get("/drivers/nonexistent/location")
    assert resp.status_code == 404


# -- GET /drivers/{id}/location/history --

@pytest.mark.asyncio
async def test_get_location_history(client, mock_location):
    """Get location history returns paginated results."""
    with patch("repository.LocationRepository.get_location_history", new_callable=AsyncMock, return_value=[mock_location]), \
         patch("repository.LocationRepository.count_locations", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/location/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["locations"]) == 1


@pytest.mark.asyncio
async def test_get_location_history_empty(client):
    """Get location history returns empty when no records exist."""
    with patch("repository.LocationRepository.get_location_history", new_callable=AsyncMock, return_value=[]), \
         patch("repository.LocationRepository.count_locations", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/location/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["locations"] == []


@pytest.mark.asyncio
async def test_get_location_history_pagination(client, mock_location):
    """Location history respects skip and limit params."""
    with patch("repository.LocationRepository.get_location_history", new_callable=AsyncMock, return_value=[mock_location]) as mock_hist, \
         patch("repository.LocationRepository.count_locations", new_callable=AsyncMock, return_value=100):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/location/history?skip=10&limit=5")
    assert resp.status_code == 200
    mock_hist.assert_called_once_with("ddd00000-0000-0000-0000-000000000001", skip=10, limit=5)
