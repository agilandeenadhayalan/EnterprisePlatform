"""Tests for payout service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

class TestCreatePayoutSchema:
    def test_valid_payout(self):
        from schemas import CreatePayoutRequest
        req = CreatePayoutRequest(driver_id="d-1", amount=150.0)
        assert req.currency == "USD"

    def test_with_period(self):
        from schemas import CreatePayoutRequest
        now = datetime.now(timezone.utc)
        req = CreatePayoutRequest(driver_id="d-1", amount=200.0, period_start=now, period_end=now)
        assert req.period_start is not None

    def test_zero_amount_fails(self):
        from schemas import CreatePayoutRequest
        with pytest.raises(ValidationError):
            CreatePayoutRequest(driver_id="d-1", amount=0)

    def test_negative_amount_fails(self):
        from schemas import CreatePayoutRequest
        with pytest.raises(ValidationError):
            CreatePayoutRequest(driver_id="d-1", amount=-50.0)

class TestPayoutResponse:
    def test_full_response(self):
        from schemas import PayoutResponse
        now = datetime.now(timezone.utc)
        resp = PayoutResponse(id="po-1", driver_id="d-1", amount=150.0, currency="USD", status="pending", created_at=now)
        assert resp.status == "pending"

    def test_list_response(self):
        from schemas import PayoutResponse, PayoutListResponse
        now = datetime.now(timezone.utc)
        payouts = [PayoutResponse(id=f"po-{i}", driver_id="d-1", amount=100.0, currency="USD", status="pending", created_at=now) for i in range(3)]
        resp = PayoutListResponse(payouts=payouts, count=3)
        assert resp.count == 3

class TestPayoutConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "payout-service"
        assert settings.service_port == 8083

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
