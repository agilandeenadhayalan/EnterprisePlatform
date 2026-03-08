"""Tests for dynamic pricing AI service — schemas, haversine, config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestPredictPriceSchema:
    def test_valid_request(self):
        from schemas import PredictPriceRequest
        req = PredictPriceRequest(
            pickup_lat=30.27, pickup_lon=-97.74,
            dropoff_lat=30.30, dropoff_lon=-97.70,
            hour_of_day=14, day_of_week=2,
        )
        assert req.vehicle_type == "economy"

    def test_invalid_latitude(self):
        from schemas import PredictPriceRequest
        with pytest.raises(ValidationError):
            PredictPriceRequest(
                pickup_lat=100.0, pickup_lon=-97.74,
                dropoff_lat=30.30, dropoff_lon=-97.70,
                hour_of_day=14, day_of_week=2,
            )

    def test_invalid_hour(self):
        from schemas import PredictPriceRequest
        with pytest.raises(ValidationError):
            PredictPriceRequest(
                pickup_lat=30.27, pickup_lon=-97.74,
                dropoff_lat=30.30, dropoff_lon=-97.70,
                hour_of_day=25, day_of_week=2,
            )


class TestHaversine:
    def test_zero_distance(self):
        from main import _haversine_distance
        dist = _haversine_distance(30.27, -97.74, 30.27, -97.74)
        assert dist == 0.0

    def test_known_distance(self):
        from main import _haversine_distance
        # Austin to Dallas is roughly 190 miles
        dist = _haversine_distance(30.27, -97.74, 32.78, -96.80)
        assert 170 < dist < 210

    def test_returns_float(self):
        from main import _haversine_distance
        assert isinstance(_haversine_distance(30.0, -97.0, 31.0, -96.0), float)


class TestHeatmapResponse:
    def test_heatmap_response(self):
        from schemas import HeatmapResponse, HeatmapCell
        cells = [HeatmapCell(lat=30.0, lon=-97.0, intensity=0.5)]
        resp = HeatmapResponse(heatmap=cells, generated_at="2024-01-01T00:00:00Z", grid_size=1)
        assert resp.grid_size == 1
        assert len(resp.heatmap) == 1


class TestDynamicPricingConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "dynamic-pricing-ai-service"
        assert settings.service_port == 8075
