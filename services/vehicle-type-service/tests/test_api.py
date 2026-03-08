"""Tests for vehicle type service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestVehicleTypeSchemas:

    def test_vehicle_type_response(self):
        from schemas import VehicleTypeResponse
        resp = VehicleTypeResponse(
            id="type-1", name="sedan", display_name="Sedan",
            capacity=4, luggage_capacity=2, is_active=True,
        )
        assert resp.name == "sedan"
        assert resp.capacity == 4

    def test_vehicle_type_with_features(self):
        from schemas import VehicleTypeResponse
        resp = VehicleTypeResponse(
            id="type-1", name="luxury", display_name="Luxury",
            capacity=4, luggage_capacity=3, is_active=True,
            features={"wifi": True, "leather_seats": True},
        )
        assert resp.features["wifi"] is True

    def test_vehicle_type_list_response(self):
        from schemas import VehicleTypeResponse, VehicleTypeListResponse
        types = [
            VehicleTypeResponse(
                id=f"type-{i}", name=f"type{i}", display_name=f"Type {i}",
                capacity=4, luggage_capacity=2, is_active=True,
            )
            for i in range(3)
        ]
        resp = VehicleTypeListResponse(vehicle_types=types, count=3)
        assert resp.count == 3

    def test_vehicle_type_list_empty(self):
        from schemas import VehicleTypeListResponse
        resp = VehicleTypeListResponse(vehicle_types=[], count=0)
        assert resp.count == 0

    def test_pricing_response(self):
        from schemas import VehicleTypePricingResponse
        resp = VehicleTypePricingResponse(
            id="type-1", name="sedan", display_name="Sedan",
            base_fare=5.0, per_km_rate=1.5,
            per_minute_rate=0.25, minimum_fare=8.0,
            currency="USD",
        )
        assert resp.base_fare == 5.0
        assert resp.per_km_rate == 1.5
        assert resp.minimum_fare == 8.0

    def test_pricing_different_currency(self):
        from schemas import VehicleTypePricingResponse
        resp = VehicleTypePricingResponse(
            id="type-1", name="sedan", display_name="Sedan",
            base_fare=50.0, per_km_rate=15.0,
            per_minute_rate=2.5, minimum_fare=80.0,
            currency="MXN",
        )
        assert resp.currency == "MXN"


class TestVehicleTypeConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "vehicle-type-service"
        assert settings.service_port == 8060

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")
