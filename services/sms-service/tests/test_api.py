"""
Tests for SMS service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestSmsSchemas:
    """Verify Pydantic schema validation for SMS requests/responses."""

    def test_sms_send_request_valid(self):
        from schemas import SmsSendRequest
        req = SmsSendRequest(to="+1234567890", message="Hello from Smart Mobility!")
        assert req.to == "+1234567890"

    def test_sms_send_otp_request_valid(self):
        from schemas import SmsSendOtpRequest
        req = SmsSendOtpRequest(to="+1234567890", otp_code="123456")
        assert req.otp_code == "123456"

    def test_sms_send_otp_request_rejects_short_code(self):
        from schemas import SmsSendOtpRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SmsSendOtpRequest(to="+1234567890", otp_code="12")

    def test_sms_send_response(self):
        from schemas import SmsSendResponse
        resp = SmsSendResponse(message_id="msg-123", to="+1234567890")
        assert resp.status == "queued"
        assert resp.provider == "twilio"

    def test_sms_status_response(self):
        from schemas import SmsStatusResponse
        resp = SmsStatusResponse(message_id="msg-123", status="delivered")
        assert resp.delivered_at is None

    def test_sms_status_response_with_details(self):
        from schemas import SmsStatusResponse
        resp = SmsStatusResponse(
            message_id="msg-123",
            status="delivered",
            to="+1234567890",
            delivered_at="2024-01-15T10:30:00Z",
        )
        assert resp.to == "+1234567890"


class TestSmsRepository:
    """Verify stubbed SMS repository logic."""

    @pytest.mark.asyncio
    async def test_send_sms_returns_message_id(self):
        from repository import SmsRepository
        repo = SmsRepository()
        msg_id = await repo.send_sms("+1234567890", "Test message")
        assert msg_id is not None

    @pytest.mark.asyncio
    async def test_send_otp_sms_returns_message_id(self):
        from repository import SmsRepository
        repo = SmsRepository()
        msg_id = await repo.send_otp_sms("+1234567890", "123456")
        assert msg_id is not None


class TestSmsConfig:
    """Verify SMS service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "sms-service"
        assert settings.service_port == 8093

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
