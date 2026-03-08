"""Tests for ride tracking service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestWaypointSchemas:

    def test_add_waypoint_valid(self):
        from schemas import AddWaypointRequest
        wp = AddWaypointRequest(latitude=40.7128, longitude=-74.0060)
        assert wp.latitude == 40.7128

    def test_add_waypoint_full(self):
        from schemas import AddWaypointRequest
        wp = AddWaypointRequest(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.5,
            speed_kmh=45.0,
            heading=180.0,
            accuracy_meters=5.0,
        )
        assert wp.speed_kmh == 45.0
        assert wp.heading == 180.0

    def test_add_waypoint_invalid_latitude(self):
        from schemas import AddWaypointRequest
        with pytest.raises(Exception):
            AddWaypointRequest(latitude=91.0, longitude=-74.0)

    def test_add_waypoint_invalid_speed(self):
        from schemas import AddWaypointRequest
        with pytest.raises(Exception):
            AddWaypointRequest(latitude=40.0, longitude=-74.0, speed_kmh=-10.0)

    def test_waypoint_response(self):
        from schemas import WaypointResponse
        resp = WaypointResponse(
            id="wp-1", trip_id="trip-1",
            latitude=40.7128, longitude=-74.0060,
            sequence_number=1,
        )
        assert resp.sequence_number == 1

    def test_track_response(self):
        from schemas import TrackResponse, WaypointResponse
        waypoints = [
            WaypointResponse(
                id=f"wp-{i}", trip_id="trip-1",
                latitude=40.0 + i * 0.001, longitude=-74.0,
                sequence_number=i,
            )
            for i in range(3)
        ]
        resp = TrackResponse(trip_id="trip-1", waypoints=waypoints, count=3)
        assert resp.count == 3

    def test_track_response_empty(self):
        from schemas import TrackResponse
        resp = TrackResponse(trip_id="trip-1", waypoints=[], count=0)
        assert resp.count == 0


class TestTrackingConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "ride-tracking-service"
        assert settings.service_port == 8052

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
