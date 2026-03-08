"""
Tests for fleet management service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestFleetSchemas:
    """Verify Pydantic schema validation for fleet responses."""

    def test_fleet_overview_response(self):
        from schemas import FleetOverviewResponse
        resp = FleetOverviewResponse(
            total_vehicles=100,
            active_vehicles=75,
            total_drivers=50,
            active_drivers=40,
            utilization_rate=75.0,
        )
        assert resp.utilization_rate == 75.0

    def test_fleet_vehicle_response(self):
        from schemas import FleetVehicleResponse
        resp = FleetVehicleResponse(
            id="veh-1", make="Tesla", model="Model 3",
            year=2024, license_plate="ABC-1234",
            status="active", vehicle_type="sedan",
        )
        assert resp.make == "Tesla"

    def test_fleet_vehicle_list_response(self):
        from schemas import FleetVehicleResponse, FleetVehicleListResponse
        vehicles = [
            FleetVehicleResponse(
                id="veh-1", make="Tesla", model="Model 3",
                year=2024, license_plate="ABC-1234",
                status="active", vehicle_type="sedan",
            )
        ]
        resp = FleetVehicleListResponse(vehicles=vehicles, count=1)
        assert resp.count == 1

    def test_fleet_driver_response(self):
        from schemas import FleetDriverResponse
        resp = FleetDriverResponse(
            id="drv-1", full_name="John Smith",
            status="active", rating=4.8, total_trips=100,
        )
        assert resp.rating == 4.8

    def test_fleet_driver_list_response(self):
        from schemas import FleetDriverResponse, FleetDriverListResponse
        drivers = [
            FleetDriverResponse(id="drv-1", full_name="John", status="active")
        ]
        resp = FleetDriverListResponse(drivers=drivers, count=1)
        assert resp.count == 1

    def test_fleet_utilization_response(self):
        from schemas import FleetUtilizationResponse
        resp = FleetUtilizationResponse(
            period="last_30_days",
            vehicle_utilization_pct=75.0,
            driver_utilization_pct=82.5,
            avg_trips_per_vehicle=45.2,
            avg_trips_per_driver=68.3,
        )
        assert resp.period == "last_30_days"


class TestFleetRepository:
    """Verify stubbed fleet repository logic."""

    @pytest.mark.asyncio
    async def test_get_overview(self):
        from repository import FleetRepository
        repo = FleetRepository()
        data = await repo.get_overview()
        assert data["total_vehicles"] > 0
        assert "utilization_rate" in data

    @pytest.mark.asyncio
    async def test_get_vehicles(self):
        from repository import FleetRepository
        repo = FleetRepository()
        vehicles = await repo.get_vehicles()
        assert len(vehicles) > 0

    @pytest.mark.asyncio
    async def test_get_drivers(self):
        from repository import FleetRepository
        repo = FleetRepository()
        drivers = await repo.get_drivers()
        assert len(drivers) > 0

    @pytest.mark.asyncio
    async def test_get_utilization(self):
        from repository import FleetRepository
        repo = FleetRepository()
        data = await repo.get_utilization()
        assert "vehicle_utilization_pct" in data


class TestFleetConfig:
    """Verify fleet management service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "fleet-management-service"
        assert settings.service_port == 8100

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
