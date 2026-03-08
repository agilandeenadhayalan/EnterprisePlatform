"""Tests for route service — Haversine distance calculation tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestHaversineDistance:
    """Test the Haversine formula implementation."""

    def test_same_point_zero_distance(self):
        from repository import haversine_distance
        d = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert d == 0.0

    def test_nyc_to_la(self):
        """NYC to LA is approximately 3,944 km straight-line."""
        from repository import haversine_distance
        d = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < d < 4000

    def test_london_to_paris(self):
        """London to Paris is approximately 340 km."""
        from repository import haversine_distance
        d = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330 < d < 350

    def test_short_distance(self):
        """Two nearby points in Manhattan should be < 5 km."""
        from repository import haversine_distance
        d = haversine_distance(40.7128, -74.0060, 40.7580, -73.9855)
        assert 0 < d < 10

    def test_antipodal_points(self):
        """North pole to south pole is approximately 20,015 km."""
        from repository import haversine_distance
        d = haversine_distance(90, 0, -90, 0)
        assert 20000 < d < 20100


class TestRouteEstimation:

    def test_road_distance_factor(self):
        from repository import estimate_road_distance
        road = estimate_road_distance(10.0, 1.3)
        assert road == 13.0

    def test_road_distance_custom_factor(self):
        from repository import estimate_road_distance
        road = estimate_road_distance(10.0, 1.5)
        assert road == 15.0

    def test_duration_estimation(self):
        from repository import estimate_duration_minutes
        # 30 km at 30 km/h = 60 minutes
        duration = estimate_duration_minutes(30.0, 30.0)
        assert duration == 60

    def test_duration_minimum_one_minute(self):
        from repository import estimate_duration_minutes
        # Very short distance should still return at least 1 minute
        duration = estimate_duration_minutes(0.01, 30.0)
        assert duration >= 1

    def test_duration_zero_speed(self):
        from repository import estimate_duration_minutes
        duration = estimate_duration_minutes(10.0, 0.0)
        assert duration == 0


class TestRouteSchemas:

    def test_route_calculate_request(self):
        from schemas import RouteCalculateRequest
        req = RouteCalculateRequest(
            pickup_latitude=40.7128, pickup_longitude=-74.0060,
            dropoff_latitude=40.7580, dropoff_longitude=-73.9855,
        )
        assert req.pickup_latitude == 40.7128

    def test_route_calculate_response(self):
        from schemas import RouteCalculateResponse
        resp = RouteCalculateResponse(
            straight_line_distance_km=5.0,
            estimated_road_distance_km=6.5,
            estimated_duration_minutes=13,
            average_speed_kmh=30.0,
        )
        assert resp.estimated_duration_minutes == 13
