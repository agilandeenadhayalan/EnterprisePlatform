"""
Test fixtures for kafka-consumer-locations.
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
def sample_location_events():
    """Sample batch of location events to archive."""
    return [
        {
            "event_id": "loc-001",
            "driver_id": "driver-001",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "heading": 90.0,
            "speed_kmh": 35.0,
            "timestamp": "2024-06-15T10:30:00",
            "status": "online",
        },
        {
            "event_id": "loc-002",
            "driver_id": "driver-002",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "heading": 180.0,
            "speed_kmh": 45.0,
            "timestamp": "2024-06-15T10:30:05",
            "status": "busy",
        },
        {
            "event_id": "loc-003",
            "driver_id": "driver-001",
            "latitude": 40.7135,
            "longitude": -74.0055,
            "heading": 95.0,
            "speed_kmh": 30.0,
            "timestamp": "2024-06-15T10:30:10",
            "status": "online",
        },
    ]
