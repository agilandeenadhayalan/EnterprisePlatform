"""
Tests for pricing service — schema validation, fare calculation logic, config.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestFareEstimateSchema:
    """Test FareEstimateRequest validation."""

    def test_valid_estimate_request(self):
        from schemas import FareEstimateRequest
        req = FareEstimateRequest(vehicle_type="economy", distance_miles=5.0, duration_minutes=15.0)
        assert req.vehicle_type == "economy"
        assert req.surge_multiplier == 1.0

    def test_with_surge(self):
        from schemas import FareEstimateRequest
        req = FareEstimateRequest(vehicle_type="premium", distance_miles=10.0, duration_minutes=25.0, surge_multiplier=1.5)
        assert req.surge_multiplier == 1.5

    def test_negative_distance_fails(self):
        from schemas import FareEstimateRequest
        with pytest.raises(ValidationError):
            FareEstimateRequest(vehicle_type="economy", distance_miles=-1.0, duration_minutes=10.0)

    def test_zero_duration_fails(self):
        from schemas import FareEstimateRequest
        with pytest.raises(ValidationError):
            FareEstimateRequest(vehicle_type="economy", distance_miles=5.0, duration_minutes=0.0)

    def test_surge_below_one_fails(self):
        from schemas import FareEstimateRequest
        with pytest.raises(ValidationError):
            FareEstimateRequest(vehicle_type="economy", distance_miles=5.0, duration_minutes=10.0, surge_multiplier=0.5)


class TestFareCalculateSchema:
    """Test FareCalculateRequest validation."""

    def test_valid_calculate_request(self):
        from schemas import FareCalculateRequest
        req = FareCalculateRequest(vehicle_type="xl", distance_miles=8.0, duration_minutes=20.0, discount_amount=5.0)
        assert req.discount_amount == 5.0

    def test_default_discount_zero(self):
        from schemas import FareCalculateRequest
        req = FareCalculateRequest(vehicle_type="economy", distance_miles=3.0, duration_minutes=10.0)
        assert req.discount_amount == 0.0


class TestPricingRuleResponse:
    """Test PricingRuleResponse shape."""

    def test_valid_rule_response(self):
        from schemas import PricingRuleResponse
        now = datetime.now(timezone.utc)
        resp = PricingRuleResponse(
            id="r-1", vehicle_type="economy", base_fare=2.50,
            per_mile_rate=1.50, per_minute_rate=0.25, booking_fee=2.50,
            minimum_fare=5.00, is_active=True, created_at=now,
        )
        assert resp.vehicle_type == "economy"
        assert resp.base_fare == 2.50

    def test_rule_list_response(self):
        from schemas import PricingRuleResponse, PricingRuleListResponse
        now = datetime.now(timezone.utc)
        rules = [
            PricingRuleResponse(
                id=f"r-{i}", vehicle_type=vt, base_fare=2.5,
                per_mile_rate=1.5, per_minute_rate=0.25, booking_fee=2.5,
                minimum_fare=5.0, is_active=True, created_at=now,
            )
            for i, vt in enumerate(["economy", "premium", "xl"])
        ]
        resp = PricingRuleListResponse(rules=rules, count=3)
        assert resp.count == 3


class TestFareEstimateResponse:
    """Test FareEstimateResponse shape."""

    def test_estimate_response_shape(self):
        from schemas import FareEstimateResponse
        resp = FareEstimateResponse(
            vehicle_type="economy", base_fare=2.50, distance_charge=7.50,
            time_charge=3.75, booking_fee=2.50, surge_multiplier=1.0,
            surge_charge=0.0, subtotal=16.25, total=16.25, minimum_fare=5.00,
        )
        assert resp.total == 16.25
        assert resp.surge_charge == 0.0


class TestPricingConfig:
    """Verify pricing service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "pricing-service"
        assert settings.service_port == 8070

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")
