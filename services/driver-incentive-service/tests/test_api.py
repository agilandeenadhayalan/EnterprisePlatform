"""
Tests for the driver incentive service API.

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
def mock_incentive():
    """Mock incentive ORM object."""
    inc = MagicMock()
    inc.id = "inc00000-0000-0000-0000-000000000001"
    inc.title = "Weekend Warrior Bonus"
    inc.description = "Complete 20 trips on weekends to earn extra"
    inc.incentive_type = "bonus"
    inc.amount = 50.00
    inc.currency = "USD"
    inc.criteria = {"min_trips": 20, "days": ["saturday", "sunday"]}
    inc.is_active = True
    inc.starts_at = datetime(2024, 6, 1)
    inc.ends_at = datetime(2024, 12, 31)
    inc.max_claims = 100
    inc.current_claims = 15
    inc.created_at = datetime(2024, 5, 15)
    inc.updated_at = datetime(2024, 5, 15)
    return inc


@pytest.fixture
def app():
    from main import app as _app
    from mobility_common.fastapi.database import get_db

    async def mock_get_db():
        yield AsyncMock()

    _app.dependency_overrides[get_db] = mock_get_db
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# -- Health check --

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# -- GET /incentives --

@pytest.mark.asyncio
async def test_list_incentives(client, mock_incentive):
    """List all incentives."""
    with patch("repository.IncentiveRepository.list_incentives", new_callable=AsyncMock, return_value=[mock_incentive]), \
         patch("repository.IncentiveRepository.count_incentives", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/incentives")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["incentives"][0]["title"] == "Weekend Warrior Bonus"


@pytest.mark.asyncio
async def test_list_incentives_empty(client):
    """List incentives returns empty when none exist."""
    with patch("repository.IncentiveRepository.list_incentives", new_callable=AsyncMock, return_value=[]), \
         patch("repository.IncentiveRepository.count_incentives", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/incentives")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# -- GET /incentives/active --

@pytest.mark.asyncio
async def test_list_active_incentives(client, mock_incentive):
    """List active incentives."""
    with patch("repository.IncentiveRepository.get_active_incentives", new_callable=AsyncMock, return_value=[mock_incentive]), \
         patch("repository.IncentiveRepository.count_active_incentives", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/incentives/active")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_active_incentives_empty(client):
    """List active incentives returns empty when none active."""
    with patch("repository.IncentiveRepository.get_active_incentives", new_callable=AsyncMock, return_value=[]), \
         patch("repository.IncentiveRepository.count_active_incentives", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/incentives/active")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# -- POST /incentives --

@pytest.mark.asyncio
async def test_create_incentive_success(client, mock_incentive):
    """Successfully create an incentive."""
    with patch("repository.IncentiveRepository.create_incentive", new_callable=AsyncMock, return_value=mock_incentive):
        resp = await client.post("/incentives", json={
            "title": "Weekend Warrior Bonus",
            "description": "Complete 20 trips on weekends to earn extra",
            "incentive_type": "bonus",
            "amount": 50.00,
            "starts_at": "2024-06-01T00:00:00",
            "ends_at": "2024-12-31T23:59:59",
            "max_claims": 100,
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Weekend Warrior Bonus"
    assert data["amount"] == 50.00


@pytest.mark.asyncio
async def test_create_incentive_missing_title(client):
    """Reject incentive without title."""
    resp = await client.post("/incentives", json={
        "amount": 50.00,
        "starts_at": "2024-06-01T00:00:00",
        "ends_at": "2024-12-31T23:59:59",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_incentive_zero_amount(client):
    """Reject incentive with zero amount."""
    resp = await client.post("/incentives", json={
        "title": "Bad Incentive",
        "amount": 0,
        "starts_at": "2024-06-01T00:00:00",
        "ends_at": "2024-12-31T23:59:59",
    })
    assert resp.status_code == 422


# -- GET /drivers/{id}/incentives --

@pytest.mark.asyncio
async def test_get_driver_incentives(client, mock_incentive):
    """Get incentives for a specific driver."""
    with patch("repository.IncentiveRepository.get_driver_incentives", new_callable=AsyncMock, return_value=[mock_incentive]):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/incentives")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_driver_incentives_empty(client):
    """Driver with no available incentives returns empty."""
    with patch("repository.IncentiveRepository.get_driver_incentives", new_callable=AsyncMock, return_value=[]):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/incentives")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
