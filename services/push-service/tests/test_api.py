"""
Tests for push service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestPushSchemas:
    """Verify Pydantic schema validation for push requests/responses."""

    def test_push_send_request_valid(self):
        from schemas import PushSendRequest
        req = PushSendRequest(
            device_token="token-abc-123",
            title="Ride Update",
            body="Your driver is arriving.",
        )
        assert req.device_token == "token-abc-123"
        assert req.data is None

    def test_push_send_request_with_data(self):
        from schemas import PushSendRequest
        req = PushSendRequest(
            device_token="token-abc-123",
            title="Ride Update",
            body="Your driver is arriving.",
            data={"ride_id": "ride-456"},
        )
        assert req.data["ride_id"] == "ride-456"

    def test_push_bulk_request_valid(self):
        from schemas import PushSendBulkRequest
        req = PushSendBulkRequest(
            device_tokens=["token-1", "token-2", "token-3"],
            title="Promo",
            body="50% off your next ride!",
        )
        assert len(req.device_tokens) == 3

    def test_push_send_response(self):
        from schemas import PushSendResponse
        resp = PushSendResponse(message_id="msg-123", status="sent")
        assert resp.status == "sent"
        assert resp.provider == "firebase"

    def test_push_bulk_response(self):
        from schemas import PushBulkResponse
        resp = PushBulkResponse(
            total=3, sent=2, failed=1, message_ids=["msg-1", "msg-2"]
        )
        assert resp.total == 3
        assert resp.failed == 1

    def test_push_status_response(self):
        from schemas import PushStatusResponse
        resp = PushStatusResponse(message_id="msg-123", status="delivered")
        assert resp.status == "delivered"
        assert resp.delivered_at is None


class TestPushRepository:
    """Verify stubbed push repository logic."""

    @pytest.mark.asyncio
    async def test_send_push_returns_message_id(self):
        from repository import PushRepository
        repo = PushRepository()
        msg_id = await repo.send_push("token-1", "Title", "Body")
        assert msg_id is not None
        assert len(msg_id) > 0

    @pytest.mark.asyncio
    async def test_send_push_bulk_counts(self):
        from repository import PushRepository
        repo = PushRepository()
        ids, sent, failed = await repo.send_push_bulk(
            ["token-1", "token-2"], "Title", "Body"
        )
        assert len(ids) == 2
        assert sent == 2
        assert failed == 0


class TestPushConfig:
    """Verify push service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "push-service"
        assert settings.service_port == 8091

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
