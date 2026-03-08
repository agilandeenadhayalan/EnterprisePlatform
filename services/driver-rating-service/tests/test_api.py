"""
Tests for the driver rating service API.

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
def mock_rating():
    """Mock rating ORM object."""
    r = MagicMock()
    r.id = "rrr00000-0000-0000-0000-000000000001"
    r.driver_id = "ddd00000-0000-0000-0000-000000000001"
    r.rider_id = "aaa00000-0000-0000-0000-000000000001"
    r.trip_id = "ttt00000-0000-0000-0000-000000000001"
    r.rating = 5
    r.comment = "Great driver!"
    r.created_at = datetime(2024, 6, 15)
    return r


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


# -- POST /ratings --

@pytest.mark.asyncio
async def test_create_rating_success(client, mock_rating):
    """Successfully submit a rating."""
    with patch("repository.RatingRepository.create_rating", new_callable=AsyncMock, return_value=mock_rating):
        resp = await client.post("/ratings", json={
            "driver_id": "ddd00000-0000-0000-0000-000000000001",
            "rider_id": "aaa00000-0000-0000-0000-000000000001",
            "trip_id": "ttt00000-0000-0000-0000-000000000001",
            "rating": 5,
            "comment": "Great driver!",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5


@pytest.mark.asyncio
async def test_create_rating_invalid_value(client):
    """Reject rating outside 1-5 range."""
    resp = await client.post("/ratings", json={
        "driver_id": "ddd00000-0000-0000-0000-000000000001",
        "rider_id": "aaa00000-0000-0000-0000-000000000001",
        "trip_id": "ttt00000-0000-0000-0000-000000000001",
        "rating": 6,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rating_zero_invalid(client):
    """Reject rating of 0."""
    resp = await client.post("/ratings", json={
        "driver_id": "ddd00000-0000-0000-0000-000000000001",
        "rider_id": "aaa00000-0000-0000-0000-000000000001",
        "trip_id": "ttt00000-0000-0000-0000-000000000001",
        "rating": 0,
    })
    assert resp.status_code == 422


# -- GET /drivers/{id}/ratings --

@pytest.mark.asyncio
async def test_list_ratings(client, mock_rating):
    """List ratings for a driver."""
    with patch("repository.RatingRepository.get_driver_ratings", new_callable=AsyncMock, return_value=[mock_rating]), \
         patch("repository.RatingRepository.count_driver_ratings", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/ratings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_ratings_empty(client):
    """List ratings returns empty for driver with no ratings."""
    with patch("repository.RatingRepository.get_driver_ratings", new_callable=AsyncMock, return_value=[]), \
         patch("repository.RatingRepository.count_driver_ratings", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/ratings")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# -- GET /drivers/{id}/rating/summary --

@pytest.mark.asyncio
async def test_rating_summary(client):
    """Get rating summary for a driver."""
    with patch("repository.RatingRepository.get_average_rating", new_callable=AsyncMock, return_value=4.5), \
         patch("repository.RatingRepository.count_driver_ratings", new_callable=AsyncMock, return_value=10), \
         patch("repository.RatingRepository.get_rating_distribution", new_callable=AsyncMock, return_value={"1": 0, "2": 0, "3": 1, "4": 3, "5": 6}):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/rating/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["average_rating"] == 4.5
    assert data["total_ratings"] == 10


@pytest.mark.asyncio
async def test_rating_summary_no_ratings(client):
    """Rating summary with no ratings returns zero avg."""
    with patch("repository.RatingRepository.get_average_rating", new_callable=AsyncMock, return_value=0.0), \
         patch("repository.RatingRepository.count_driver_ratings", new_callable=AsyncMock, return_value=0), \
         patch("repository.RatingRepository.get_rating_distribution", new_callable=AsyncMock, return_value={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/rating/summary")
    assert resp.status_code == 200
    assert resp.json()["average_rating"] == 0.0


@pytest.mark.asyncio
async def test_rating_distribution_sums_correctly(client):
    """Rating distribution values should sum to total_ratings."""
    dist = {"1": 2, "2": 3, "3": 5, "4": 10, "5": 30}
    total = sum(dist.values())
    with patch("repository.RatingRepository.get_average_rating", new_callable=AsyncMock, return_value=4.2), \
         patch("repository.RatingRepository.count_driver_ratings", new_callable=AsyncMock, return_value=total), \
         patch("repository.RatingRepository.get_rating_distribution", new_callable=AsyncMock, return_value=dist):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/rating/summary")
    data = resp.json()
    assert sum(data["rating_distribution"].values()) == data["total_ratings"]
