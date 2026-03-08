"""
Tests for the driver availability service API.

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
def mock_availability():
    """Mock availability ORM object."""
    record = MagicMock()
    record.id = "aaa00000-0000-0000-0000-000000000001"
    record.driver_id = "ddd00000-0000-0000-0000-000000000001"
    record.status = "online"
    record.latitude = 40.7128
    record.longitude = -74.0060
    record.last_online_at = datetime(2024, 6, 15, 10, 0, 0)
    record.last_offline_at = None
    record.total_online_seconds = 3600
    record.created_at = datetime(2024, 1, 1)
    record.updated_at = datetime(2024, 6, 15, 10, 0, 0)
    return record


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


# -- POST /drivers/{id}/online --

@pytest.mark.asyncio
async def test_go_online_success(client, mock_availability):
    """Successfully set driver online."""
    with patch("repository.AvailabilityRepository.set_online", new_callable=AsyncMock, return_value=mock_availability):
        resp = await client.post("/drivers/ddd00000-0000-0000-0000-000000000001/online", json={
            "latitude": 40.7128,
            "longitude": -74.0060,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_go_online_publishes_event(client, mock_availability, mock_producer):
    """Going online publishes a status event."""
    with patch("repository.AvailabilityRepository.set_online", new_callable=AsyncMock, return_value=mock_availability):
        await client.post("/drivers/ddd00000-0000-0000-0000-000000000001/online", json={})
    mock_producer.send_event.assert_called_once()


# -- POST /drivers/{id}/offline --

@pytest.mark.asyncio
async def test_go_offline_success(client, mock_availability):
    """Successfully set driver offline."""
    mock_availability.status = "offline"
    with patch("repository.AvailabilityRepository.set_offline", new_callable=AsyncMock, return_value=mock_availability):
        resp = await client.post("/drivers/ddd00000-0000-0000-0000-000000000001/offline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "offline"


@pytest.mark.asyncio
async def test_go_offline_publishes_event(client, mock_availability, mock_producer):
    """Going offline publishes a status event."""
    with patch("repository.AvailabilityRepository.set_offline", new_callable=AsyncMock, return_value=mock_availability):
        await client.post("/drivers/ddd00000-0000-0000-0000-000000000001/offline")
    mock_producer.send_event.assert_called_once()


# -- GET /drivers/{id}/status --

@pytest.mark.asyncio
async def test_get_status_success(client, mock_availability):
    """Get driver status returns current availability."""
    with patch("repository.AvailabilityRepository.get_by_driver_id", new_callable=AsyncMock, return_value=mock_availability):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


@pytest.mark.asyncio
async def test_get_status_not_found(client):
    """Get status returns 404 for unknown driver."""
    with patch("repository.AvailabilityRepository.get_by_driver_id", new_callable=AsyncMock, return_value=None):
        resp = await client.get("/drivers/nonexistent/status")
    assert resp.status_code == 404


# -- GET /available --

@pytest.mark.asyncio
async def test_list_available_drivers(client, mock_availability):
    """List available drivers returns online drivers."""
    with patch("repository.AvailabilityRepository.get_available_drivers", new_callable=AsyncMock, return_value=[mock_availability]), \
         patch("repository.AvailabilityRepository.count_available", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/available")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["drivers"]) == 1


@pytest.mark.asyncio
async def test_list_available_drivers_empty(client):
    """List available drivers returns empty when none online."""
    with patch("repository.AvailabilityRepository.get_available_drivers", new_callable=AsyncMock, return_value=[]), \
         patch("repository.AvailabilityRepository.count_available", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/available")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
