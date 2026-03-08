"""
Tests for dispatch service — scoring algorithm, schema validation, config.

Tests verify:
1. Scoring algorithm produces correct results across edge cases
2. Schema validation works correctly (Pydantic models)
3. Config loads with correct defaults
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestScoringAlgorithm:
    """Test the driver scoring algorithm edge cases."""

    def test_perfect_driver_nearby(self):
        """Ideal driver: close, high rating, high acceptance, low cancellation."""
        from scoring import score_driver
        score = score_driver(distance=1.0, rating=5.0, acceptance_rate=1.0, cancellation_rate=0.0)
        assert score > 75.0  # Should be high

    def test_far_away_driver(self):
        """Far driver gets lower score than nearby driver."""
        from scoring import score_driver
        near = score_driver(distance=1.0, rating=4.5, acceptance_rate=0.9, cancellation_rate=0.05)
        far = score_driver(distance=15.0, rating=4.5, acceptance_rate=0.9, cancellation_rate=0.05)
        assert near > far

    def test_distance_at_zero(self):
        """Zero distance should give maximum distance score."""
        from scoring import score_driver
        score = score_driver(distance=0.0, rating=5.0, acceptance_rate=1.0, cancellation_rate=0.0)
        assert score == 85.0  # 30 + 30 + 25 - 0

    def test_distance_beyond_max(self):
        """Distance > 20 miles should be clamped — distance score = 0."""
        from scoring import score_driver
        score_20 = score_driver(distance=20.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.1)
        score_30 = score_driver(distance=30.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.1)
        assert score_20 == score_30  # Both clamped to max distance

    def test_low_rating_driver(self):
        """Low-rated driver should score lower than high-rated driver."""
        from scoring import score_driver
        high = score_driver(distance=5.0, rating=4.8, acceptance_rate=0.9, cancellation_rate=0.05)
        low = score_driver(distance=5.0, rating=2.0, acceptance_rate=0.9, cancellation_rate=0.05)
        assert high > low

    def test_high_cancellation_penalty(self):
        """Driver with high cancellation rate should be penalized."""
        from scoring import score_driver
        reliable = score_driver(distance=5.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.05)
        flaky = score_driver(distance=5.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.5)
        assert reliable > flaky

    def test_zero_everything(self):
        """All zeros should produce zero score."""
        from scoring import score_driver
        score = score_driver(distance=20.0, rating=0.0, acceptance_rate=0.0, cancellation_rate=0.0)
        assert score == 0.0

    def test_score_never_negative(self):
        """Score floor is 0 even with maximum penalties."""
        from scoring import score_driver
        score = score_driver(distance=20.0, rating=0.0, acceptance_rate=0.0, cancellation_rate=1.0)
        assert score >= 0.0

    def test_negative_distance_clamped(self):
        """Negative distance treated as 0."""
        from scoring import score_driver
        score = score_driver(distance=-5.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.1)
        score_zero = score_driver(distance=0.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.1)
        assert score == score_zero

    def test_score_returns_float(self):
        """Score should always be a float."""
        from scoring import score_driver
        score = score_driver(distance=5.0, rating=4.0, acceptance_rate=0.8, cancellation_rate=0.1)
        assert isinstance(score, float)


class TestDispatchSchemas:
    """Verify Pydantic schema validation for dispatch requests/responses."""

    def test_dispatch_request_valid(self):
        """A DispatchRequest with all fields should validate."""
        from schemas import DispatchRequest
        req = DispatchRequest(
            trip_id="trip-123",
            driver_id="driver-456",
            distance_to_pickup=3.5,
            driver_rating=4.8,
            acceptance_rate=0.95,
            cancellation_rate=0.02,
        )
        assert req.trip_id == "trip-123"
        assert req.distance_to_pickup == 3.5

    def test_dispatch_request_minimal(self):
        """Only trip_id and driver_id are required."""
        from schemas import DispatchRequest
        req = DispatchRequest(trip_id="trip-1", driver_id="drv-1")
        assert req.distance_to_pickup is None
        assert req.driver_rating is None

    def test_dispatch_request_invalid_rating(self):
        """Rating > 5 should fail validation."""
        from schemas import DispatchRequest
        with pytest.raises(ValidationError):
            DispatchRequest(trip_id="t", driver_id="d", driver_rating=6.0)

    def test_dispatch_assignment_response(self):
        """DispatchAssignmentResponse should validate with all fields."""
        from schemas import DispatchAssignmentResponse
        now = datetime.now(timezone.utc)
        resp = DispatchAssignmentResponse(
            id="a-1", trip_id="t-1", driver_id="d-1",
            status="pending", score=72.5,
            distance_to_pickup=3.2,
            assigned_at=now, created_at=now,
        )
        assert resp.status == "pending"
        assert resp.score == 72.5

    def test_zone_response(self):
        """DispatchZoneResponse should validate with all fields."""
        from schemas import DispatchZoneResponse
        now = datetime.now(timezone.utc)
        zone = DispatchZoneResponse(
            id="z-1", name="Downtown", city="Austin",
            lat_min=30.25, lat_max=30.30, lon_min=-97.75, lon_max=-97.70,
            is_active=True, created_at=now,
        )
        assert zone.name == "Downtown"
        assert zone.city == "Austin"


class TestDispatchConfig:
    """Verify dispatch service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings
        assert settings.service_name == "dispatch-service"
        assert settings.service_port == 8061

    def test_kafka_config(self):
        """Kafka bootstrap servers should be configured."""
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")
