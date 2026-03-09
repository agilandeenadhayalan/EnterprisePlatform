"""
Test fixtures for kafka-consumer-rides.
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
def sample_ride_events():
    """Sample batch of ride events to archive."""
    return [
        {
            "event_id": "evt-001",
            "ride_id": "ride-001",
            "driver_id": "driver-001",
            "rider_id": "rider-001",
            "fare_amount": 25.50,
            "pickup_at": "2024-06-15T08:30:00",
            "dropoff_at": "2024-06-15T08:55:00",
        },
        {
            "event_id": "evt-002",
            "ride_id": "ride-002",
            "driver_id": "driver-002",
            "rider_id": "rider-002",
            "fare_amount": 18.00,
            "pickup_at": "2024-06-15T09:00:00",
            "dropoff_at": "2024-06-15T09:20:00",
        },
    ]
