"""Tests for payment service — schema validation, config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestCreatePaymentSchema:
    def test_valid_payment(self):
        from schemas import CreatePaymentRequest
        req = CreatePaymentRequest(trip_id="t-1", rider_id="r-1", amount=25.50)
        assert req.currency == "USD"

    def test_with_all_fields(self):
        from schemas import CreatePaymentRequest
        req = CreatePaymentRequest(
            trip_id="t-1", rider_id="r-1", driver_id="d-1",
            amount=30.0, currency="EUR", payment_method_id="pm-1",
        )
        assert req.driver_id == "d-1"

    def test_zero_amount_fails(self):
        from schemas import CreatePaymentRequest
        with pytest.raises(ValidationError):
            CreatePaymentRequest(trip_id="t-1", rider_id="r-1", amount=0)

    def test_negative_amount_fails(self):
        from schemas import CreatePaymentRequest
        with pytest.raises(ValidationError):
            CreatePaymentRequest(trip_id="t-1", rider_id="r-1", amount=-5.0)


class TestUpdateStatusSchema:
    def test_valid_completed(self):
        from schemas import UpdatePaymentStatusRequest
        req = UpdatePaymentStatusRequest(status="completed")
        assert req.status == "completed"

    def test_valid_failed(self):
        from schemas import UpdatePaymentStatusRequest
        req = UpdatePaymentStatusRequest(status="failed", payment_gateway_ref="gw-ref-123")
        assert req.payment_gateway_ref == "gw-ref-123"

    def test_invalid_status(self):
        from schemas import UpdatePaymentStatusRequest
        with pytest.raises(ValidationError):
            UpdatePaymentStatusRequest(status="cancelled")

    def test_all_valid_statuses(self):
        from schemas import UpdatePaymentStatusRequest
        for s in ["pending", "processing", "completed", "failed", "refunded"]:
            req = UpdatePaymentStatusRequest(status=s)
            assert req.status == s


class TestPaymentResponse:
    def test_full_response(self):
        from schemas import PaymentResponse
        now = datetime.now(timezone.utc)
        resp = PaymentResponse(
            id="p-1", trip_id="t-1", rider_id="r-1", driver_id="d-1",
            amount=25.50, currency="USD", status="completed",
            created_at=now, updated_at=now,
        )
        assert resp.amount == 25.50

    def test_minimal_response(self):
        from schemas import PaymentResponse
        now = datetime.now(timezone.utc)
        resp = PaymentResponse(
            id="p-1", trip_id="t-1", rider_id="r-1",
            amount=10.0, currency="USD", status="pending",
            created_at=now, updated_at=now,
        )
        assert resp.driver_id is None


class TestPaymentConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "payment-service"
        assert settings.service_port == 8080

    def test_kafka(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
