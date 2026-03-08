"""
Tests for the driver service API.

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
def mock_driver():
    """Mock driver ORM object."""
    driver = MagicMock()
    driver.id = "660e8400-e29b-41d4-a716-446655440001"
    driver.user_id = "550e8400-e29b-41d4-a716-446655440000"
    driver.first_name = "John"
    driver.last_name = "Doe"
    driver.email = "john.driver@test.com"
    driver.phone = "+1234567890"
    driver.license_number = "DL-12345"
    driver.vehicle_type = "sedan"
    driver.vehicle_make = "Toyota"
    driver.vehicle_model = "Camry"
    driver.vehicle_year = 2022
    driver.vehicle_plate = "ABC-1234"
    driver.rating = 4.8
    driver.total_trips = 150
    driver.acceptance_rate = 0.92
    driver.is_active = True
    driver.is_verified = True
    driver.status = "online"
    driver.latitude = 40.7128
    driver.longitude = -74.0060
    driver.created_at = datetime(2024, 1, 1)
    driver.updated_at = datetime(2024, 1, 1)
    return driver


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
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


# -- POST /drivers --


@pytest.mark.asyncio
async def test_register_driver_success(client, mock_driver):
    """Successfully register a new driver."""
    with patch("repository.DriverRepository.get_driver_by_email", new_callable=AsyncMock, return_value=None), \
         patch("repository.DriverRepository.create_driver", new_callable=AsyncMock, return_value=mock_driver):
        resp = await client.post("/drivers", json={
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.driver@test.com",
            "phone": "+1234567890",
            "license_number": "DL-12345",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "john.driver@test.com"
    assert data["first_name"] == "John"


@pytest.mark.asyncio
async def test_register_driver_duplicate_email(client, mock_driver):
    """Reject duplicate email registration."""
    with patch("repository.DriverRepository.get_driver_by_email", new_callable=AsyncMock, return_value=mock_driver):
        resp = await client.post("/drivers", json={
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.driver@test.com",
            "phone": "+1234567890",
            "license_number": "DL-12345",
        })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_driver_publishes_event(client, mock_driver, mock_producer):
    """Registration publishes a driver.registered event."""
    with patch("repository.DriverRepository.get_driver_by_email", new_callable=AsyncMock, return_value=None), \
         patch("repository.DriverRepository.create_driver", new_callable=AsyncMock, return_value=mock_driver):
        await client.post("/drivers", json={
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.driver@test.com",
            "phone": "+1234567890",
            "license_number": "DL-12345",
        })
    mock_producer.send_event.assert_called_once()


# -- GET /drivers --


@pytest.mark.asyncio
async def test_list_drivers(client, mock_driver):
    """List drivers returns paginated results."""
    with patch("repository.DriverRepository.list_drivers", new_callable=AsyncMock, return_value=[mock_driver]), \
         patch("repository.DriverRepository.count_drivers", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/drivers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["drivers"]) == 1


@pytest.mark.asyncio
async def test_list_drivers_empty(client):
    """List drivers returns empty list when no drivers exist."""
    with patch("repository.DriverRepository.list_drivers", new_callable=AsyncMock, return_value=[]), \
         patch("repository.DriverRepository.count_drivers", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/drivers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["drivers"] == []


# -- GET /drivers/{id} --


@pytest.mark.asyncio
async def test_get_driver_success(client, mock_driver):
    """Get driver by ID returns driver data."""
    with patch("repository.DriverRepository.get_driver_by_id", new_callable=AsyncMock, return_value=mock_driver):
        resp = await client.get(f"/drivers/{mock_driver.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(mock_driver.id)


@pytest.mark.asyncio
async def test_get_driver_not_found(client):
    """Get driver returns 404 for nonexistent ID."""
    with patch("repository.DriverRepository.get_driver_by_id", new_callable=AsyncMock, return_value=None):
        resp = await client.get("/drivers/nonexistent-id")
    assert resp.status_code == 404


# -- PATCH /drivers/{id} --


@pytest.mark.asyncio
async def test_update_driver_success(client, mock_driver):
    """Update driver fields successfully."""
    updated = MagicMock()
    for attr in dir(mock_driver):
        if not attr.startswith("_"):
            try:
                setattr(updated, attr, getattr(mock_driver, attr))
            except (AttributeError, TypeError):
                pass
    updated.first_name = "Jane"
    with patch("repository.DriverRepository.get_driver_by_id", new_callable=AsyncMock, return_value=mock_driver), \
         patch("repository.DriverRepository.update_driver", new_callable=AsyncMock, return_value=updated):
        resp = await client.patch(f"/drivers/{mock_driver.id}", json={"first_name": "Jane"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Jane"


@pytest.mark.asyncio
async def test_update_driver_not_found(client):
    """Update returns 404 for nonexistent driver."""
    with patch("repository.DriverRepository.get_driver_by_id", new_callable=AsyncMock, return_value=None):
        resp = await client.patch("/drivers/nonexistent-id", json={"first_name": "Jane"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_driver_no_changes(client, mock_driver):
    """Update with empty body returns current driver."""
    with patch("repository.DriverRepository.get_driver_by_id", new_callable=AsyncMock, return_value=mock_driver):
        resp = await client.patch(f"/drivers/{mock_driver.id}", json={})
    assert resp.status_code == 200


# -- GET /drivers/nearby --


@pytest.mark.asyncio
async def test_nearby_drivers(client, mock_driver):
    """Find nearby drivers returns results."""
    with patch("repository.DriverRepository.find_nearby_drivers", new_callable=AsyncMock, return_value=[mock_driver]):
        resp = await client.get("/drivers/nearby", params={
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius_km": 5.0,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
