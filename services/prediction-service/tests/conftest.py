"""
Test fixtures for prediction service.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import repository


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_repo():
    """Reset the in-memory repository before each test (re-seed data)."""
    repository.repo = repository.PredictionRepository(seed=True)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
