"""
Test fixtures for stream-dedup-service.
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
def sample_unique_events():
    """Batch of events with unique IDs."""
    return [
        {"event_id": "evt-001", "data": "first"},
        {"event_id": "evt-002", "data": "second"},
        {"event_id": "evt-003", "data": "third"},
    ]


@pytest.fixture
def sample_duplicate_events():
    """Batch with duplicate event IDs."""
    return [
        {"event_id": "evt-001", "data": "first"},
        {"event_id": "evt-002", "data": "second"},
        {"event_id": "evt-001", "data": "first-dup"},
        {"event_id": "evt-003", "data": "third"},
        {"event_id": "evt-002", "data": "second-dup"},
    ]
