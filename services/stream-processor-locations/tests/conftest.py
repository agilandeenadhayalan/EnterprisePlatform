"""
Test fixtures for stream-processor-locations.
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
def sample_location_event():
    """Sample location event in Manhattan Midtown."""
    return {
        "event_id": "loc-001",
        "driver_id": "driver-001",
        "latitude": 40.7550,
        "longitude": -73.9850,
        "heading": 90.0,
        "speed_kmh": 35.0,
        "accuracy_meters": 5.0,
        "timestamp": "2024-06-15T10:30:00",
        "status": "online",
        "ride_id": None,
    }


@pytest.fixture
def sample_brooklyn_event():
    """Sample location event in Brooklyn."""
    return {
        "event_id": "loc-002",
        "driver_id": "driver-002",
        "latitude": 40.6500,
        "longitude": -73.9500,
        "heading": 180.0,
        "speed_kmh": 50.0,
        "accuracy_meters": 8.0,
        "timestamp": "2024-06-15T10:35:00",
        "status": "busy",
        "ride_id": "ride-100",
    }
