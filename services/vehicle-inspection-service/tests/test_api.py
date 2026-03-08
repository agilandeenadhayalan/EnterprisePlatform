"""Tests for vehicle inspection service."""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestInspectionSchemas:

    def test_create_inspection_valid(self):
        from schemas import CreateInspectionRequest
        req = CreateInspectionRequest(
            vehicle_id="v-1", inspection_type="annual",
        )
        assert req.inspection_type == "annual"

    def test_create_inspection_full(self):
        from schemas import CreateInspectionRequest
        now = datetime.now(timezone.utc)
        req = CreateInspectionRequest(
            vehicle_id="v-1", inspector_id="insp-1",
            inspection_type="pre_trip",
            notes="Routine check", scheduled_at=now,
        )
        assert req.notes == "Routine check"

    def test_update_status_request(self):
        from schemas import UpdateInspectionStatusRequest
        req = UpdateInspectionStatusRequest(
            status="passed",
            findings={"brakes": "good", "tires": "good"},
        )
        assert req.status == "passed"
        assert req.findings["brakes"] == "good"

    def test_inspection_response(self):
        from schemas import InspectionResponse
        resp = InspectionResponse(
            id="insp-1", vehicle_id="v-1",
            inspection_type="annual", status="scheduled",
        )
        assert resp.status == "scheduled"

    def test_inspection_list_response(self):
        from schemas import InspectionResponse, InspectionListResponse
        items = [
            InspectionResponse(
                id=f"insp-{i}", vehicle_id="v-1",
                inspection_type="annual", status="scheduled",
            )
            for i in range(3)
        ]
        resp = InspectionListResponse(inspections=items, count=3)
        assert resp.count == 3

    def test_inspection_list_empty(self):
        from schemas import InspectionListResponse
        resp = InspectionListResponse(inspections=[], count=0)
        assert resp.count == 0


class TestInspectionStatusValidation:

    def test_valid_statuses(self):
        from repository import VALID_STATUSES
        assert "scheduled" in VALID_STATUSES
        assert "passed" in VALID_STATUSES
        assert "failed" in VALID_STATUSES
        assert "cancelled" in VALID_STATUSES

    def test_invalid_status_not_in_list(self):
        from repository import VALID_STATUSES
        assert "approved" not in VALID_STATUSES


class TestInspectionConfig:

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "vehicle-inspection-service"
        assert settings.service_port == 8058

    def test_database_url(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")
