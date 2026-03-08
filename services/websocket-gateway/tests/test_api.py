"""
Tests for WebSocket gateway — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestWsSchemas:
    """Verify Pydantic schema validation for WebSocket gateway requests/responses."""

    def test_broadcast_request_valid(self):
        from schemas import BroadcastRequest
        req = BroadcastRequest(
            channel="rides",
            event="ride_update",
            data={"ride_id": "ride-123", "status": "in_progress"},
        )
        assert req.channel == "rides"
        assert req.user_ids is None

    def test_broadcast_request_with_targets(self):
        from schemas import BroadcastRequest
        req = BroadcastRequest(
            channel="notifications",
            event="new_notification",
            data={"title": "Hello"},
            user_ids=["user-1", "user-2"],
        )
        assert len(req.user_ids) == 2

    def test_broadcast_response(self):
        from schemas import BroadcastResponse
        resp = BroadcastResponse(channel="rides", event="update", recipients=5)
        assert resp.message == "Broadcast sent"

    def test_ws_info_response(self):
        from schemas import WsInfoResponse
        resp = WsInfoResponse(
            active_connections=150,
            max_connections=10000,
            uptime_seconds=3600,
            channels=["rides", "notifications"],
        )
        assert resp.active_connections == 150
        assert len(resp.channels) == 2

    def test_ws_info_response_empty(self):
        from schemas import WsInfoResponse
        resp = WsInfoResponse(
            active_connections=0,
            max_connections=10000,
            uptime_seconds=0,
            channels=[],
        )
        assert resp.channels == []


class TestWsRepository:
    """Verify stubbed WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_broadcast_returns_zero_for_empty_channel(self):
        from repository import WsConnectionManager
        mgr = WsConnectionManager()
        count = await mgr.broadcast("rides", "update", {"test": True})
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_info_returns_stats(self):
        from repository import WsConnectionManager
        mgr = WsConnectionManager()
        info = await mgr.get_info()
        assert info["active_connections"] == 0
        assert isinstance(info["uptime_seconds"], int)


class TestWsConfig:
    """Verify WebSocket gateway configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "websocket-gateway"
        assert settings.service_port == 8096

    def test_ws_settings(self):
        from config import settings
        assert settings.ws_max_connections == 10000

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
