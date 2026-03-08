"""Tests for refund service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

class TestCreateRefundSchema:
    def test_valid_refund(self):
        from schemas import CreateRefundRequest
        req = CreateRefundRequest(payment_id="p-1", rider_id="r-1", amount=25.0, reason="Trip cancelled")
        assert req.amount == 25.0

    def test_zero_amount_fails(self):
        from schemas import CreateRefundRequest
        with pytest.raises(ValidationError):
            CreateRefundRequest(payment_id="p-1", rider_id="r-1", amount=0)

    def test_optional_reason(self):
        from schemas import CreateRefundRequest
        req = CreateRefundRequest(payment_id="p-1", rider_id="r-1", amount=10.0)
        assert req.reason is None

class TestApproveRefundSchema:
    def test_valid_approve(self):
        from schemas import ApproveRefundRequest
        req = ApproveRefundRequest(approved_by="admin-1")
        assert req.approved_by == "admin-1"

class TestRefundResponse:
    def test_full_response(self):
        from schemas import RefundResponse
        now = datetime.now(timezone.utc)
        resp = RefundResponse(id="rf-1", payment_id="p-1", rider_id="r-1", amount=15.0, status="pending", created_at=now, updated_at=now)
        assert resp.status == "pending"

    def test_approved_response(self):
        from schemas import RefundResponse
        now = datetime.now(timezone.utc)
        resp = RefundResponse(id="rf-1", payment_id="p-1", rider_id="r-1", amount=15.0, status="approved", approved_by="admin-1", created_at=now, updated_at=now)
        assert resp.approved_by == "admin-1"

    def test_list_response(self):
        from schemas import RefundResponse, RefundListResponse
        now = datetime.now(timezone.utc)
        refunds = [RefundResponse(id=f"rf-{i}", payment_id="p-1", rider_id="r-1", amount=10.0, status="pending", created_at=now, updated_at=now) for i in range(2)]
        resp = RefundListResponse(refunds=refunds, count=2)
        assert resp.count == 2

class TestRefundConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "refund-service"
        assert settings.service_port == 8082

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
