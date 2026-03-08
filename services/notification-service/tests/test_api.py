"""
Tests for notification service — schema validation, config, and imports.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestNotificationSchemas:
    """Verify Pydantic schema validation for notification requests/responses."""

    def test_create_notification_request_valid(self):
        from schemas import CreateNotificationRequest
        req = CreateNotificationRequest(
            user_id="user-123",
            title="Ride Completed",
            message="Your ride to downtown has been completed.",
        )
        assert req.user_id == "user-123"
        assert req.notification_type == "info"
        assert req.channel == "in_app"

    def test_create_notification_request_custom_type(self):
        from schemas import CreateNotificationRequest
        req = CreateNotificationRequest(
            user_id="user-123",
            title="Payment Alert",
            message="Your payment method is expiring.",
            notification_type="warning",
            channel="push",
        )
        assert req.notification_type == "warning"
        assert req.channel == "push"

    def test_notification_response_valid(self):
        from schemas import NotificationResponse
        now = datetime.now(timezone.utc)
        resp = NotificationResponse(
            id="notif-1",
            user_id="user-1",
            title="Test",
            message="Test message",
            notification_type="info",
            channel="in_app",
            is_read=False,
            created_at=now,
        )
        assert resp.is_read is False
        assert resp.read_at is None

    def test_notification_response_read(self):
        from schemas import NotificationResponse
        now = datetime.now(timezone.utc)
        resp = NotificationResponse(
            id="notif-1",
            user_id="user-1",
            title="Test",
            message="Test message",
            notification_type="info",
            channel="in_app",
            is_read=True,
            read_at=now,
            created_at=now,
        )
        assert resp.is_read is True
        assert resp.read_at is not None

    def test_notification_list_response(self):
        from schemas import NotificationResponse, NotificationListResponse
        now = datetime.now(timezone.utc)
        notifications = [
            NotificationResponse(
                id=f"notif-{i}",
                user_id="user-1",
                title=f"Title {i}",
                message=f"Message {i}",
                notification_type="info",
                channel="in_app",
                is_read=False,
                created_at=now,
            )
            for i in range(3)
        ]
        resp = NotificationListResponse(notifications=notifications, count=3)
        assert resp.count == 3
        assert len(resp.notifications) == 3

    def test_notification_list_empty(self):
        from schemas import NotificationListResponse
        resp = NotificationListResponse(notifications=[], count=0)
        assert resp.count == 0

    def test_unread_count_response(self):
        from schemas import UnreadCountResponse
        resp = UnreadCountResponse(user_id="user-1", unread_count=5)
        assert resp.unread_count == 5

    def test_mark_read_response(self):
        from schemas import MarkReadResponse
        resp = MarkReadResponse(count=3)
        assert resp.message == "Marked as read"
        assert resp.count == 3

    def test_mark_all_read_request(self):
        from schemas import MarkAllReadRequest
        req = MarkAllReadRequest(user_id="user-123")
        assert req.user_id == "user-123"


class TestNotificationConfig:
    """Verify notification service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "notification-service"
        assert settings.service_port == 8090

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
