"""
Tests for trip service — schema validation, config, and repository logic.

No database needed — these are pure unit tests with mocked dependencies.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Schema Tests ──

class TestTripSchemas:
    """Verify Pydantic schema validation for trip requests/responses."""

    def test_create_trip_request_valid(self):
        from schemas import CreateTripRequest
        req = CreateTripRequest(
            rider_id="550e8400-e29b-41d4-a716-446655440000",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
        )
        assert req.rider_id == "550e8400-e29b-41d4-a716-446655440000"
        assert req.pickup_latitude == 40.7128

    def test_create_trip_request_with_addresses(self):
        from schemas import CreateTripRequest
        req = CreateTripRequest(
            rider_id="rider-1",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            pickup_address="123 Main St, NYC",
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
            dropoff_address="456 Broadway, NYC",
            vehicle_type="sedan",
        )
        assert req.pickup_address == "123 Main St, NYC"
        assert req.vehicle_type == "sedan"

    def test_create_trip_invalid_latitude(self):
        from schemas import CreateTripRequest
        with pytest.raises(Exception):
            CreateTripRequest(
                rider_id="rider-1",
                pickup_latitude=91.0,  # Invalid: > 90
                pickup_longitude=-74.0060,
                dropoff_latitude=40.0,
                dropoff_longitude=-74.0,
            )

    def test_create_trip_invalid_longitude(self):
        from schemas import CreateTripRequest
        with pytest.raises(Exception):
            CreateTripRequest(
                rider_id="rider-1",
                pickup_latitude=40.0,
                pickup_longitude=-181.0,  # Invalid: < -180
                dropoff_latitude=40.0,
                dropoff_longitude=-74.0,
            )

    def test_update_trip_status_request(self):
        from schemas import UpdateTripStatusRequest
        req = UpdateTripStatusRequest(
            status="driver_assigned",
            driver_id="driver-1",
        )
        assert req.status == "driver_assigned"
        assert req.driver_id == "driver-1"

    def test_trip_response_full(self):
        from schemas import TripResponse
        now = datetime.now(timezone.utc)
        resp = TripResponse(
            id="trip-1",
            rider_id="rider-1",
            driver_id="driver-1",
            status="in_progress",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
            fare_amount=25.50,
            currency="USD",
            created_at=now,
        )
        assert resp.fare_amount == 25.50
        assert resp.currency == "USD"

    def test_trip_response_minimal(self):
        from schemas import TripResponse
        resp = TripResponse(
            id="trip-1",
            rider_id="rider-1",
            status="requested",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
        )
        assert resp.driver_id is None
        assert resp.fare_amount is None

    def test_trip_list_response(self):
        from schemas import TripResponse, TripListResponse
        trips = [
            TripResponse(
                id=f"trip-{i}",
                rider_id="rider-1",
                status="requested",
                pickup_latitude=40.0,
                pickup_longitude=-74.0,
                dropoff_latitude=41.0,
                dropoff_longitude=-73.0,
            )
            for i in range(3)
        ]
        resp = TripListResponse(trips=trips, count=3)
        assert resp.count == 3
        assert len(resp.trips) == 3

    def test_trip_list_empty(self):
        from schemas import TripListResponse
        resp = TripListResponse(trips=[], count=0)
        assert resp.count == 0


# ── Config Tests ──

class TestTripConfig:
    """Verify trip service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "trip-service"
        assert settings.service_port == 8050

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"


# ── Repository Logic Tests ──

class TestTripStatusTransitions:
    """Verify the trip status state machine."""

    def test_valid_transitions_from_requested(self):
        from repository import VALID_TRANSITIONS
        assert "driver_assigned" in VALID_TRANSITIONS["requested"]
        assert "cancelled" in VALID_TRANSITIONS["requested"]

    def test_valid_transitions_from_in_progress(self):
        from repository import VALID_TRANSITIONS
        assert "completed" in VALID_TRANSITIONS["in_progress"]
        assert "cancelled" in VALID_TRANSITIONS["in_progress"]

    def test_no_transitions_from_completed(self):
        from repository import VALID_TRANSITIONS
        assert VALID_TRANSITIONS["completed"] == []

    def test_no_transitions_from_cancelled(self):
        from repository import VALID_TRANSITIONS
        assert VALID_TRANSITIONS["cancelled"] == []

    def test_full_happy_path(self):
        """Verify the complete status flow: requested -> completed."""
        from repository import VALID_TRANSITIONS
        path = ["requested", "driver_assigned", "driver_en_route", "arrived", "in_progress", "completed"]
        for i in range(len(path) - 1):
            assert path[i + 1] in VALID_TRANSITIONS[path[i]], (
                f"Transition {path[i]} -> {path[i+1]} should be valid"
            )
