"""Tests for fare calculation service — calculation logic, schemas, config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestFareCalculation:
    """Test core fare calculation logic."""

    def test_basic_fare(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=2.50, distance_miles=5.0, per_mile_rate=1.50,
            duration_minutes=15.0, per_minute_rate=0.25, booking_fee=2.50,
        )
        assert result["distance_charge"] == 7.50
        assert result["time_charge"] == 3.75
        assert result["total"] == 16.25

    def test_minimum_fare_applied(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=0.50, distance_miles=0.1, per_mile_rate=0.10,
            duration_minutes=1.0, per_minute_rate=0.05, booking_fee=0.50,
            minimum_fare=5.00,
        )
        assert result["total"] == 5.00
        assert result["minimum_fare_applied"] is True

    def test_no_minimum_fare(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=5.0, distance_miles=10.0, per_mile_rate=2.0,
            duration_minutes=20.0, per_minute_rate=0.50, booking_fee=3.0,
        )
        assert result["minimum_fare_applied"] is False

    def test_with_surge(self):
        from main import _calculate_fare
        no_surge = _calculate_fare(
            base_fare=2.0, distance_miles=5.0, per_mile_rate=1.50,
            duration_minutes=10.0, per_minute_rate=0.25, booking_fee=2.0,
        )
        with_surge = _calculate_fare(
            base_fare=2.0, distance_miles=5.0, per_mile_rate=1.50,
            duration_minutes=10.0, per_minute_rate=0.25, booking_fee=2.0,
            surge_multiplier=2.0,
        )
        assert with_surge["total"] > no_surge["total"]
        assert with_surge["surge_charge"] > 0

    def test_with_discount(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=2.0, distance_miles=5.0, per_mile_rate=1.50,
            duration_minutes=10.0, per_minute_rate=0.25, booking_fee=2.0,
            discount_amount=3.0,
        )
        assert result["discount_amount"] == 3.0

    def test_discount_below_minimum(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=2.0, distance_miles=1.0, per_mile_rate=1.0,
            duration_minutes=5.0, per_minute_rate=0.20, booking_fee=1.0,
            discount_amount=100.0, minimum_fare=5.0,
        )
        assert result["total"] == 5.0

    def test_zero_distance_and_time(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=2.0, distance_miles=0.0, per_mile_rate=1.50,
            duration_minutes=0.0, per_minute_rate=0.25, booking_fee=2.0,
        )
        assert result["distance_charge"] == 0.0
        assert result["time_charge"] == 0.0

    def test_surge_charge_only_on_distance_and_time(self):
        from main import _calculate_fare
        result = _calculate_fare(
            base_fare=3.0, distance_miles=10.0, per_mile_rate=1.0,
            duration_minutes=10.0, per_minute_rate=0.50, booking_fee=2.0,
            surge_multiplier=2.0,
        )
        # Surge should apply to distance (10) + time (5) = 15, so surge_charge = 15
        assert result["surge_charge"] == 15.0


class TestFareSchemas:
    def test_valid_calculate_request(self):
        from schemas import FareCalculateRequest
        req = FareCalculateRequest(
            base_fare=2.0, distance_miles=5.0, per_mile_rate=1.5,
            duration_minutes=10.0, per_minute_rate=0.25,
        )
        assert req.booking_fee == 2.50

    def test_negative_distance_fails(self):
        from schemas import FareCalculateRequest
        with pytest.raises(ValidationError):
            FareCalculateRequest(
                base_fare=2.0, distance_miles=-1.0, per_mile_rate=1.5,
                duration_minutes=10.0, per_minute_rate=0.25,
            )

    def test_surge_below_one_fails(self):
        from schemas import FareWithSurgeRequest
        with pytest.raises(ValidationError):
            FareWithSurgeRequest(
                base_fare=2.0, distance_miles=5.0, per_mile_rate=1.5,
                duration_minutes=10.0, per_minute_rate=0.25,
                surge_multiplier=0.5,
            )

    def test_breakdown_response(self):
        from schemas import FareBreakdownResponse
        resp = FareBreakdownResponse(
            base_fare=2.0, distance_charge=7.5, time_charge=3.75,
            booking_fee=2.5, surge_multiplier=1.0, surge_charge=0.0,
            discount_amount=0.0, subtotal=15.75, total=15.75,
            minimum_fare_applied=False,
        )
        assert resp.total == 15.75


class TestFareCalcConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "fare-calculation-service"
        assert settings.service_port == 8074
