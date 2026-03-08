"""
Tests for the driver matching service API and scoring algorithm.

Pure unit tests — no DB needed (service is stateless).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

import repository
import schemas


@pytest.fixture
def mock_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.send_event = AsyncMock(return_value=True)
    return producer


@pytest.fixture
def app(mock_producer):
    """Create test app with mocked dependencies."""
    from main import app as _app
    _app.state.producer = mock_producer
    yield _app


@pytest.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# -- Scoring algorithm unit tests --


class TestHaversineDistance:
    """Test the Haversine distance calculation."""

    def test_same_point_zero_distance(self):
        """Same point should have zero distance."""
        d = repository.haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert d == 0.0

    def test_known_distance(self):
        """NYC to Newark is roughly 14-16 km."""
        d = repository.haversine_distance(40.7128, -74.0060, 40.7357, -74.1724)
        assert 13.0 < d < 17.0

    def test_symmetric(self):
        """Distance A→B should equal distance B→A."""
        d1 = repository.haversine_distance(40.7128, -74.0060, 40.7580, -73.9855)
        d2 = repository.haversine_distance(40.7580, -73.9855, 40.7128, -74.0060)
        assert abs(d1 - d2) < 0.001


class TestComputeScore:
    """Test the scoring function."""

    def test_perfect_score_nearby(self):
        """Driver right at pickup with perfect stats gets near-perfect score."""
        score = repository.compute_score(
            distance_km=0.0, rating=5.0, acceptance_rate=1.0, max_distance_km=10.0,
        )
        assert score == 1.0

    def test_far_driver_lower_score(self):
        """Driver at max distance gets lower score."""
        score = repository.compute_score(
            distance_km=10.0, rating=5.0, acceptance_rate=1.0, max_distance_km=10.0,
        )
        # Distance component is 0, rating and acceptance still contribute
        assert score < 1.0
        assert score > 0.0

    def test_low_rating_lower_score(self):
        """Lower rating reduces score."""
        high = repository.compute_score(0.0, 5.0, 1.0)
        low = repository.compute_score(0.0, 2.0, 1.0)
        assert high > low

    def test_low_acceptance_lower_score(self):
        """Lower acceptance rate reduces score."""
        high = repository.compute_score(0.0, 5.0, 1.0)
        low = repository.compute_score(0.0, 5.0, 0.3)
        assert high > low

    def test_score_between_zero_and_one(self):
        """Score should always be in [0, 1] range."""
        score = repository.compute_score(5.0, 3.0, 0.5)
        assert 0.0 <= score <= 1.0


class TestMatchDrivers:
    """Test the matching logic."""

    def test_match_returns_ranked_candidates(self):
        """Match returns candidates ranked by score."""
        request = schemas.MatchRequest(
            trip_id="trip-001",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            candidates=[
                schemas.DriverCandidate(driver_id="d1", latitude=40.7130, longitude=-74.0062, rating=4.5, acceptance_rate=0.9),
                schemas.DriverCandidate(driver_id="d2", latitude=40.7500, longitude=-74.0500, rating=5.0, acceptance_rate=1.0),
            ],
        )
        result = repository.match_drivers(request)
        assert result.total_candidates == 2
        assert result.total_eligible >= 1
        assert result.candidates[0].rank == 1
        # Closer driver should rank higher (d1 is much closer)
        assert result.best_match.driver_id == "d1"

    def test_match_filters_by_distance(self):
        """Candidates beyond max_distance_km are excluded."""
        request = schemas.MatchRequest(
            trip_id="trip-002",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            max_distance_km=1.0,
            candidates=[
                schemas.DriverCandidate(driver_id="d1", latitude=40.7130, longitude=-74.0062, rating=5.0, acceptance_rate=1.0),
                schemas.DriverCandidate(driver_id="d2", latitude=41.0000, longitude=-74.5000, rating=5.0, acceptance_rate=1.0),
            ],
        )
        result = repository.match_drivers(request)
        assert result.total_eligible == 1
        assert result.candidates[0].driver_id == "d1"

    def test_match_filters_by_vehicle_type(self):
        """Vehicle type preference filters candidates."""
        request = schemas.MatchRequest(
            trip_id="trip-003",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            vehicle_type_preference="suv",
            candidates=[
                schemas.DriverCandidate(driver_id="d1", latitude=40.7130, longitude=-74.0062, vehicle_type="sedan"),
                schemas.DriverCandidate(driver_id="d2", latitude=40.7130, longitude=-74.0062, vehicle_type="suv"),
            ],
        )
        result = repository.match_drivers(request)
        assert result.total_eligible == 1
        assert result.candidates[0].driver_id == "d2"


# -- API endpoint tests --


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_match_endpoint(client):
    """POST /match returns ranked candidates."""
    resp = await client.post("/match", json={
        "trip_id": "trip-100",
        "pickup_latitude": 40.7128,
        "pickup_longitude": -74.0060,
        "candidates": [
            {"driver_id": "d1", "latitude": 40.7130, "longitude": -74.0062, "rating": 4.8, "acceptance_rate": 0.95},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["trip_id"] == "trip-100"
    assert data["total_eligible"] == 1


@pytest.mark.asyncio
async def test_get_candidates_cached(client):
    """GET /candidates returns cached match results."""
    # First do a match to populate cache
    await client.post("/match", json={
        "trip_id": "trip-cached",
        "pickup_latitude": 40.7128,
        "pickup_longitude": -74.0060,
        "candidates": [
            {"driver_id": "d1", "latitude": 40.7130, "longitude": -74.0062, "rating": 4.8, "acceptance_rate": 0.95},
        ],
    })
    resp = await client.get("/candidates/trip-cached")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trip_id"] == "trip-cached"


@pytest.mark.asyncio
async def test_get_candidates_not_found(client):
    """GET /candidates returns 404 for unknown trip."""
    resp = await client.get("/candidates/nonexistent")
    assert resp.status_code == 404
