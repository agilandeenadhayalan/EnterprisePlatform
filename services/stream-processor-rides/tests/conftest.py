"""
Test fixtures for stream-processor-rides.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app, _repo
import repository


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_repo():
    """Reset the repository before each test."""
    _repo.processed_rides.clear()
    _repo.reset_stats()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_ride_event():
    """Sample ride event data."""
    return {
        "event_id": "evt-001",
        "ride_id": "ride-001",
        "driver_id": "driver-001",
        "rider_id": "rider-001",
        "pickup_latitude": 40.7128,
        "pickup_longitude": -74.0060,
        "dropoff_latitude": 40.7580,
        "dropoff_longitude": -73.9855,
        "pickup_zone_id": 161,
        "dropoff_zone_id": 162,
        "ride_status": "completed",
        "fare_amount": 25.50,
        "tip_amount": 5.00,
        "distance_miles": 3.2,
        "pickup_at": "2024-06-15T08:30:00",
        "dropoff_at": "2024-06-15T08:55:00",
        "vehicle_type": "sedan",
        "payment_method": "card",
        "surge_multiplier": 1.2,
    }


@pytest.fixture
def sample_weekend_event():
    """Ride event on a weekend (Saturday)."""
    return {
        "event_id": "evt-002",
        "ride_id": "ride-002",
        "driver_id": "driver-002",
        "rider_id": "rider-002",
        "pickup_latitude": 40.7500,
        "pickup_longitude": -73.9900,
        "dropoff_latitude": 40.7300,
        "dropoff_longitude": -73.9950,
        "ride_status": "completed",
        "fare_amount": 15.00,
        "tip_amount": 3.00,
        "distance_miles": 1.5,
        "pickup_at": "2024-06-15T22:00:00",  # Saturday
        "dropoff_at": "2024-06-15T22:20:00",
        "vehicle_type": "suv",
        "payment_method": "cash",
        "surge_multiplier": 1.5,
    }
