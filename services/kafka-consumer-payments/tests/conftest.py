"""
Test fixtures for kafka-consumer-payments.
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
def sample_payment_event():
    """Sample payment event."""
    return {
        "event_id": "pay-evt-001",
        "payment_id": "pay-001",
        "ride_id": "ride-001",
        "rider_id": "rider-001",
        "driver_id": "driver-001",
        "amount": 25.50,
        "tip_amount": 5.00,
        "payment_method": "card",
        "currency": "USD",
        "status": "completed",
        "processor": "stripe",
        "timestamp": "2024-06-15T08:55:00",
    }


@pytest.fixture
def sample_payment_events():
    """Batch of payment events."""
    return [
        {
            "event_id": "pay-evt-001",
            "payment_id": "pay-001",
            "ride_id": "ride-001",
            "rider_id": "rider-001",
            "driver_id": "driver-001",
            "amount": 25.50,
            "tip_amount": 5.00,
            "payment_method": "card",
            "currency": "USD",
            "status": "completed",
            "processor": "stripe",
            "timestamp": "2024-06-15T08:55:00",
        },
        {
            "event_id": "pay-evt-002",
            "payment_id": "pay-002",
            "ride_id": "ride-002",
            "rider_id": "rider-002",
            "driver_id": "driver-002",
            "amount": 18.00,
            "tip_amount": 3.00,
            "payment_method": "wallet",
            "currency": "USD",
            "status": "completed",
            "processor": "internal",
            "timestamp": "2024-06-15T09:20:00",
        },
    ]
