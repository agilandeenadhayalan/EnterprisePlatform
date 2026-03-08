"""
Tests for presence service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestPresenceSchemas:
    """Verify Pydantic schema validation for presence requests/responses."""

    def test_heartbeat_request_defaults(self):
        from schemas import HeartbeatRequest
        req = HeartbeatRequest()
        assert req.status == "online"

    def test_heartbeat_request_custom_status(self):
        from schemas import HeartbeatRequest
        req = HeartbeatRequest(status="away")
        assert req.status == "away"

    def test_heartbeat_response(self):
        from schemas import HeartbeatResponse
        resp = HeartbeatResponse(user_id="user-1", status="online", ttl_seconds=60)
        assert resp.message == "Heartbeat recorded"

    def test_presence_response_online(self):
        from schemas import PresenceResponse
        resp = PresenceResponse(user_id="user-1", is_online=True, status="online")
        assert resp.is_online is True

    def test_presence_response_offline(self):
        from schemas import PresenceResponse
        resp = PresenceResponse(user_id="user-1", is_online=False)
        assert resp.status is None

    def test_online_count_response(self):
        from schemas import OnlineCountResponse
        resp = OnlineCountResponse(online_count=42)
        assert resp.online_count == 42


class TestPresenceRepository:
    """Verify in-memory presence repository logic."""

    @pytest.mark.asyncio
    async def test_heartbeat_makes_user_online(self):
        from repository import PresenceRepository
        repo = PresenceRepository(ttl_seconds=60)
        await repo.record_heartbeat("user-1", "online")
        data = await repo.get_presence("user-1")
        assert data["is_online"] is True

    @pytest.mark.asyncio
    async def test_unknown_user_returns_none(self):
        from repository import PresenceRepository
        repo = PresenceRepository(ttl_seconds=60)
        data = await repo.get_presence("unknown-user")
        assert data is None


class TestPresenceConfig:
    """Verify presence service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "presence-service"
        assert settings.service_port == 8095

    def test_heartbeat_ttl(self):
        from config import settings
        assert settings.heartbeat_ttl_seconds == 60

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
