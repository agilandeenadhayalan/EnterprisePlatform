"""
Test fixtures for stream-processor-metrics.
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
def sample_metric_event():
    """Sample metric event for ride fare."""
    return {
        "event_id": "met-001",
        "metric_name": "ride_fare",
        "metric_value": 25.50,
        "dimensions": {"zone": "manhattan", "vehicle_type": "sedan"},
        "timestamp": "2024-06-15T10:30:15",
        "source": "ride-service",
    }


@pytest.fixture
def sample_metric_events_same_window():
    """Multiple metric events that fall in the same 1-minute window."""
    return [
        {
            "event_id": "met-001",
            "metric_name": "ride_fare",
            "metric_value": 25.50,
            "dimensions": {"zone": "manhattan"},
            "timestamp": "2024-06-15T10:30:15",
            "source": "ride-service",
        },
        {
            "event_id": "met-002",
            "metric_name": "ride_fare",
            "metric_value": 18.00,
            "dimensions": {"zone": "manhattan"},
            "timestamp": "2024-06-15T10:30:30",
            "source": "ride-service",
        },
        {
            "event_id": "met-003",
            "metric_name": "ride_fare",
            "metric_value": 42.00,
            "dimensions": {"zone": "manhattan"},
            "timestamp": "2024-06-15T10:30:45",
            "source": "ride-service",
        },
    ]


@pytest.fixture
def sample_metric_events_different_windows():
    """Metric events in different 1-minute windows."""
    return [
        {
            "event_id": "met-010",
            "metric_name": "ride_distance",
            "metric_value": 3.2,
            "dimensions": {},
            "timestamp": "2024-06-15T10:30:15",
            "source": "ride-service",
        },
        {
            "event_id": "met-011",
            "metric_name": "ride_distance",
            "metric_value": 5.1,
            "dimensions": {},
            "timestamp": "2024-06-15T10:31:15",
            "source": "ride-service",
        },
    ]
