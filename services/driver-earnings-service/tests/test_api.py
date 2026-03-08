"""
Tests for the driver earnings service API.

Pure unit tests — mock the repository layer, no DB needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, date


@pytest.fixture
def mock_earning():
    """Mock earning ORM object."""
    e = MagicMock()
    e.id = "eee00000-0000-0000-0000-000000000001"
    e.driver_id = "ddd00000-0000-0000-0000-000000000001"
    e.trip_id = "ttt00000-0000-0000-0000-000000000001"
    e.amount = 25.50
    e.currency = "USD"
    e.earning_type = "trip"
    e.description = "Trip fare"
    e.earning_date = date(2024, 6, 15)
    e.created_at = datetime(2024, 6, 15, 12, 0, 0)
    return e


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


# -- GET /drivers/{id}/earnings --

@pytest.mark.asyncio
async def test_list_earnings(client, mock_earning):
    """List earnings for a driver."""
    with patch("repository.EarningsRepository.get_earnings", new_callable=AsyncMock, return_value=[mock_earning]), \
         patch("repository.EarningsRepository.count_earnings", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["earnings"][0]["amount"] == 25.50


@pytest.mark.asyncio
async def test_list_earnings_empty(client):
    """List earnings returns empty for driver with no earnings."""
    with patch("repository.EarningsRepository.get_earnings", new_callable=AsyncMock, return_value=[]), \
         patch("repository.EarningsRepository.count_earnings", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# -- GET /drivers/{id}/earnings/daily --

@pytest.mark.asyncio
async def test_daily_earnings(client):
    """Get daily aggregated earnings."""
    daily_data = [
        {"date": date(2024, 6, 15), "total_amount": 125.00, "trip_count": 5},
        {"date": date(2024, 6, 14), "total_amount": 98.50, "trip_count": 4},
    ]
    with patch("repository.EarningsRepository.get_daily_earnings", new_callable=AsyncMock, return_value=daily_data):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 2
    assert data["daily_earnings"][0]["total_amount"] == 125.00


@pytest.mark.asyncio
async def test_daily_earnings_with_date_range(client):
    """Daily earnings accepts date range params."""
    with patch("repository.EarningsRepository.get_daily_earnings", new_callable=AsyncMock, return_value=[]) as mock_daily:
        resp = await client.get(
            "/drivers/ddd00000-0000-0000-0000-000000000001/earnings/daily",
            params={"start_date": "2024-06-01", "end_date": "2024-06-30"},
        )
    assert resp.status_code == 200
    mock_daily.assert_called_once()


@pytest.mark.asyncio
async def test_daily_earnings_empty(client):
    """Daily earnings returns empty list when no data."""
    with patch("repository.EarningsRepository.get_daily_earnings", new_callable=AsyncMock, return_value=[]):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings/daily")
    assert resp.status_code == 200
    assert resp.json()["total_days"] == 0


# -- GET /drivers/{id}/earnings/summary --

@pytest.mark.asyncio
async def test_earnings_summary(client):
    """Get earnings summary."""
    summary = {"total_earnings": 5000.00, "total_trips": 200, "average_per_trip": 25.00}
    with patch("repository.EarningsRepository.get_earnings_summary", new_callable=AsyncMock, return_value=summary):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_earnings"] == 5000.00
    assert data["average_per_trip"] == 25.00


@pytest.mark.asyncio
async def test_earnings_summary_no_data(client):
    """Earnings summary with no data returns zeros."""
    summary = {"total_earnings": 0.0, "total_trips": 0, "average_per_trip": 0.0}
    with patch("repository.EarningsRepository.get_earnings_summary", new_callable=AsyncMock, return_value=summary):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_earnings"] == 0.0
    assert data["total_trips"] == 0


@pytest.mark.asyncio
async def test_earnings_summary_currency(client):
    """Earnings summary includes currency."""
    summary = {"total_earnings": 100.0, "total_trips": 5, "average_per_trip": 20.0}
    with patch("repository.EarningsRepository.get_earnings_summary", new_callable=AsyncMock, return_value=summary):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/earnings/summary")
    assert resp.json()["currency"] == "USD"
