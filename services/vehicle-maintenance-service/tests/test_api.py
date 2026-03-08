"""Tests for vehicle maintenance service."""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestMaintenanceSchemas:

    def test_create_maintenance_valid(self):
        from schemas import CreateMaintenanceRequest
        req = CreateMaintenanceRequest(
            vehicle_id="v-1", maintenance_type="oil_change",
        )
        assert req.maintenance_type == "oil_change"

    def test_create_maintenance_full(self):
        from schemas import CreateMaintenanceRequest
        now = datetime.now(timezone.utc)
        req = CreateMaintenanceRequest(
            vehicle_id="v-1", maintenance_type="tire_rotation",
            description="Rotate all 4 tires", cost=49.99,
            service_provider="Quick Lube",
            scheduled_at=now,
            next_due_at=now + timedelta(days=180),
        )
        assert req.cost == 49.99
        assert req.service_provider == "Quick Lube"

    def test_create_maintenance_invalid_cost(self):
        from schemas import CreateMaintenanceRequest
        with pytest.raises(Exception):
            CreateMaintenanceRequest(
                vehicle_id="v-1", maintenance_type="oil_change",
                cost=-10.0,
            )

    def test_maintenance_response(self):
        from schemas import MaintenanceResponse
        resp = MaintenanceResponse(
            id="m-1", vehicle_id="v-1",
            maintenance_type="oil_change", status="scheduled",
        )
        assert resp.status == "scheduled"

    def test_maintenance_response_defaults(self):
        from schemas import MaintenanceResponse
        resp = MaintenanceResponse(
            id="m-1", vehicle_id="v-1",
            maintenance_type="oil_change", status="scheduled",
        )
        assert resp.currency == "USD"
        assert resp.cost is None

    def test_maintenance_list_response(self):
        from schemas import MaintenanceResponse, MaintenanceListResponse
        records = [
            MaintenanceResponse(
                id=f"m-{i}", vehicle_id="v-1",
                maintenance_type="oil_change", status="scheduled",
            )
            for i in range(3)
        ]
        resp = MaintenanceListResponse(records=records, count=3)
        assert resp.count == 3

    def test_maintenance_list_empty(self):
        from schemas import MaintenanceListResponse
        resp = MaintenanceListResponse(records=[], count=0)
        assert resp.count == 0


class TestMaintenanceConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "vehicle-maintenance-service"
        assert settings.service_port == 8059

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
