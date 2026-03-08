"""Tests for toll service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError

class TestTollEstimation:
    def test_short_distance_no_toll(self):
        from main import _estimate_toll
        assert _estimate_toll(3.0, "car") == 0.0

    def test_highway_distance_has_toll(self):
        from main import _estimate_toll
        toll = _estimate_toll(20.0, "car")
        assert toll > 0

    def test_truck_higher_rate(self):
        from main import _estimate_toll
        car_toll = _estimate_toll(20.0, "car")
        truck_toll = _estimate_toll(20.0, "truck")
        assert truck_toll > car_toll

    def test_unknown_vehicle_uses_default(self):
        from main import _estimate_toll
        toll = _estimate_toll(20.0, "unknown")
        assert toll == _estimate_toll(20.0, "car")

    def test_haversine_zero_distance(self):
        from main import _haversine
        assert _haversine(30.0, -97.0, 30.0, -97.0) == 0.0

    def test_haversine_returns_positive(self):
        from main import _haversine
        dist = _haversine(30.0, -97.0, 31.0, -96.0)
        assert dist > 0

class TestTollSchemas:
    def test_valid_calculate_request(self):
        from schemas import TollCalculateRequest
        req = TollCalculateRequest(route_points=[{"lat": 30.0, "lon": -97.0}, {"lat": 30.5, "lon": -96.5}])
        assert len(req.route_points) == 2

    def test_too_few_points_fails(self):
        from schemas import TollCalculateRequest
        with pytest.raises(ValidationError):
            TollCalculateRequest(route_points=[{"lat": 30.0, "lon": -97.0}])

class TestTollConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "toll-service"
        assert settings.service_port == 8086
