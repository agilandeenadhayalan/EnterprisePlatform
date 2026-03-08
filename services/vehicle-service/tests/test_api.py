"""Tests for vehicle service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestVehicleSchemas:

    def test_create_vehicle_valid(self):
        from schemas import CreateVehicleRequest
        v = CreateVehicleRequest(
            make="Toyota", model="Camry", year=2023,
            color="White", license_plate="ABC-1234",
        )
        assert v.make == "Toyota"
        assert v.capacity == 4  # default

    def test_create_vehicle_full(self):
        from schemas import CreateVehicleRequest
        v = CreateVehicleRequest(
            driver_id="driver-1", vehicle_type_id="type-1",
            make="Honda", model="Civic", year=2024,
            color="Black", license_plate="XYZ-5678",
            vin="1HGCG5655WA040664", capacity=5,
        )
        assert v.vin == "1HGCG5655WA040664"
        assert v.capacity == 5

    def test_create_vehicle_invalid_year(self):
        from schemas import CreateVehicleRequest
        with pytest.raises(Exception):
            CreateVehicleRequest(
                make="Toyota", model="Camry", year=1800,
                color="White", license_plate="ABC-1234",
            )

    def test_create_vehicle_invalid_capacity(self):
        from schemas import CreateVehicleRequest
        with pytest.raises(Exception):
            CreateVehicleRequest(
                make="Toyota", model="Camry", year=2023,
                color="White", license_plate="ABC-1234",
                capacity=0,
            )

    def test_update_vehicle_partial(self):
        from schemas import UpdateVehicleRequest
        update = UpdateVehicleRequest(status="maintenance")
        assert update.status == "maintenance"
        assert update.color is None

    def test_vehicle_response(self):
        from schemas import VehicleResponse
        resp = VehicleResponse(
            id="v-1", make="Toyota", model="Camry",
            year=2023, color="White", license_plate="ABC-1234",
            status="active", capacity=4, is_active=True,
        )
        assert resp.status == "active"

    def test_vehicle_list_response(self):
        from schemas import VehicleResponse, VehicleListResponse
        vehicles = [
            VehicleResponse(
                id=f"v-{i}", make="Toyota", model="Camry",
                year=2023, color="White", license_plate=f"ABC-{i}",
                status="active", capacity=4, is_active=True,
            )
            for i in range(3)
        ]
        resp = VehicleListResponse(vehicles=vehicles, count=3)
        assert resp.count == 3

    def test_vehicle_status_response(self):
        from schemas import VehicleStatusResponse
        resp = VehicleStatusResponse(id="v-1", status="active", is_active=True)
        assert resp.is_active is True

    def test_vehicle_list_empty(self):
        from schemas import VehicleListResponse
        resp = VehicleListResponse(vehicles=[], count=0)
        assert resp.count == 0


class TestVehicleConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "vehicle-service"
        assert settings.service_port == 8057

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
