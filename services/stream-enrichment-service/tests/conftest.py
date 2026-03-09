"""
Test fixtures for stream-enrichment-service.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app, _repo


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_repo():
    """Reset the repository before each test."""
    _repo.reset()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_ride_event():
    """Sample ride event with zone IDs for enrichment."""
    return {
        "event_id": "evt-001",
        "event_type": "ride",
        "pickup_zone_id": 161,
        "dropoff_zone_id": 237,
        "timestamp": "2024-06-15T08:30:00",
        "payload": {
            "ride_id": "ride-001",
            "fare_amount": 25.50,
        },
    }


@pytest.fixture
def sample_event_no_zones():
    """Event without zone IDs."""
    return {
        "event_id": "evt-002",
        "event_type": "location",
        "timestamp": "2024-06-15T10:15:00",
        "payload": {
            "driver_id": "driver-001",
            "latitude": 40.7128,
            "longitude": -74.0060,
        },
    }


@pytest.fixture
def sample_event_rainy():
    """Event during rainy weather."""
    return {
        "event_id": "evt-003",
        "event_type": "ride",
        "pickup_zone_id": 43,
        "dropoff_zone_id": 230,
        "timestamp": "2024-06-15T14:30:00",
        "payload": {"ride_id": "ride-003"},
    }
