"""
Tests for ride request service.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestRideRequestSchemas:

    def test_create_request_valid(self):
        from schemas import CreateRideRequestRequest
        req = CreateRideRequestRequest(
            rider_id="rider-1",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
        )
        assert req.rider_id == "rider-1"

    def test_create_request_with_address(self):
        from schemas import CreateRideRequestRequest
        req = CreateRideRequestRequest(
            rider_id="rider-1",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            pickup_address="Times Square",
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
            dropoff_address="Central Park",
            vehicle_type="suv",
        )
        assert req.pickup_address == "Times Square"
        assert req.vehicle_type == "suv"

    def test_create_request_invalid_latitude(self):
        from schemas import CreateRideRequestRequest
        with pytest.raises(Exception):
            CreateRideRequestRequest(
                rider_id="rider-1",
                pickup_latitude=91.0,
                pickup_longitude=-74.0,
                dropoff_latitude=40.0,
                dropoff_longitude=-74.0,
            )

    def test_ride_request_response(self):
        from schemas import RideRequestResponse
        resp = RideRequestResponse(
            id="req-1",
            rider_id="rider-1",
            status="pending",
            pickup_latitude=40.7128,
            pickup_longitude=-74.0060,
            dropoff_latitude=40.7580,
            dropoff_longitude=-73.9855,
        )
        assert resp.status == "pending"

    def test_ride_request_status_response(self):
        from schemas import RideRequestStatusResponse
        resp = RideRequestStatusResponse(id="req-1", status="pending")
        assert resp.id == "req-1"

    def test_response_optional_fields(self):
        from schemas import RideRequestResponse
        resp = RideRequestResponse(
            id="req-1",
            rider_id="rider-1",
            status="pending",
            pickup_latitude=40.0,
            pickup_longitude=-74.0,
            dropoff_latitude=41.0,
            dropoff_longitude=-73.0,
        )
        assert resp.estimated_fare is None
        assert resp.vehicle_type is None


class TestRideRequestConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "ride-request-service"
        assert settings.service_port == 8051

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"


class TestCommonImports:

    def test_event_producer_import(self):
        from mobility_common.kafka import EventProducer
        assert EventProducer is not None

    def test_topics_import(self):
        from mobility_common.kafka import Topics
        assert Topics.RIDE_REQUESTS == "ride.requests.v1"
