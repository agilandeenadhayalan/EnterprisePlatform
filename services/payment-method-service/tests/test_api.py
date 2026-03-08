"""Tests for payment method service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

class TestCreatePaymentMethodSchema:
    def test_valid_card(self):
        from schemas import CreatePaymentMethodRequest
        req = CreatePaymentMethodRequest(user_id="u-1", method_type="card", provider="visa", last_four="4242", expiry_month="12", expiry_year="2025")
        assert req.method_type == "card"

    def test_valid_wallet(self):
        from schemas import CreatePaymentMethodRequest
        req = CreatePaymentMethodRequest(user_id="u-1", method_type="wallet")
        assert req.provider is None

    def test_invalid_type(self):
        from schemas import CreatePaymentMethodRequest
        with pytest.raises(ValidationError):
            CreatePaymentMethodRequest(user_id="u-1", method_type="bitcoin")

    def test_last_four_too_short(self):
        from schemas import CreatePaymentMethodRequest
        with pytest.raises(ValidationError):
            CreatePaymentMethodRequest(user_id="u-1", method_type="card", last_four="42")

    def test_last_four_too_long(self):
        from schemas import CreatePaymentMethodRequest
        with pytest.raises(ValidationError):
            CreatePaymentMethodRequest(user_id="u-1", method_type="card", last_four="42424")

class TestPaymentMethodResponse:
    def test_full_response(self):
        from schemas import PaymentMethodResponse
        now = datetime.now(timezone.utc)
        resp = PaymentMethodResponse(id="pm-1", user_id="u-1", method_type="card", provider="visa", last_four="4242", is_default=True, is_active=True, created_at=now)
        assert resp.is_default is True

    def test_list_response(self):
        from schemas import PaymentMethodResponse, PaymentMethodListResponse
        now = datetime.now(timezone.utc)
        methods = [PaymentMethodResponse(id=f"pm-{i}", user_id="u-1", method_type="card", is_default=i==0, is_active=True, created_at=now) for i in range(3)]
        resp = PaymentMethodListResponse(payment_methods=methods, count=3)
        assert resp.count == 3

    def test_minimal_response(self):
        from schemas import PaymentMethodResponse
        now = datetime.now(timezone.utc)
        resp = PaymentMethodResponse(id="pm-1", user_id="u-1", method_type="wallet", is_default=False, is_active=True, created_at=now)
        assert resp.provider is None

class TestPaymentMethodConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "payment-method-service"
        assert settings.service_port == 8081

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
