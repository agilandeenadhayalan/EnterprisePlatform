"""
Tests for activity service — schema validation and serialization.

These tests verify:
1. ActivityResponse serializes correctly with JSONB metadata
2. LogActivityRequest validates required and optional fields
3. ActivityListResponse wraps paginated data
4. Config loads with correct defaults

No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestActivitySchemas:
    """Verify Pydantic schema validation for activity responses."""

    def test_activity_response_full(self):
        """An ActivityResponse with all fields should validate."""
        from schemas import ActivityResponse

        now = datetime.now(timezone.utc)
        activity = ActivityResponse(
            id=1,
            user_id="550e8400-e29b-41d4-a716-446655440000",
            action="login",
            resource_type="session",
            resource_id="session-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"browser": "Chrome", "os": "Windows"},
            created_at=now,
        )
        assert activity.action == "login"
        assert activity.metadata["browser"] == "Chrome"

    def test_activity_response_minimal(self):
        """ActivityResponse with only required fields."""
        from schemas import ActivityResponse

        now = datetime.now(timezone.utc)
        activity = ActivityResponse(
            id=42,
            user_id="user-id",
            action="page_view",
            created_at=now,
        )
        assert activity.id == 42
        assert activity.resource_type is None
        assert activity.metadata is None

    def test_activity_serialization(self):
        """ActivityResponse should serialize to dict with all fields."""
        from schemas import ActivityResponse

        now = datetime.now(timezone.utc)
        activity = ActivityResponse(
            id=1,
            user_id="user-id",
            action="ride_request",
            resource_type="ride",
            resource_id="ride-456",
            metadata={"pickup": "downtown", "dropoff": "airport"},
            created_at=now,
        )
        data = activity.model_dump()
        assert data["action"] == "ride_request"
        assert data["metadata"]["pickup"] == "downtown"
        assert "id" in data


class TestLogActivityRequest:
    """Verify log activity request validation."""

    def test_valid_log_request(self):
        """LogActivityRequest with all fields should validate."""
        from schemas import LogActivityRequest

        req = LogActivityRequest(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            action="login",
            resource_type="session",
            resource_id="session-123",
            ip_address="10.0.0.1",
            user_agent="curl/7.68",
            metadata={"method": "password"},
        )
        assert req.action == "login"
        assert req.metadata["method"] == "password"

    def test_minimal_log_request(self):
        """LogActivityRequest with only required fields."""
        from schemas import LogActivityRequest

        req = LogActivityRequest(
            user_id="user-id",
            action="logout",
        )
        assert req.user_id == "user-id"
        assert req.resource_type is None
        assert req.metadata is None

    def test_missing_user_id(self):
        """user_id is required."""
        from schemas import LogActivityRequest

        with pytest.raises(Exception):
            LogActivityRequest(action="login")

    def test_missing_action(self):
        """action is required."""
        from schemas import LogActivityRequest

        with pytest.raises(Exception):
            LogActivityRequest(user_id="user-id")

    def test_metadata_various_types(self):
        """metadata JSONB should accept different value types."""
        from schemas import LogActivityRequest

        req = LogActivityRequest(
            user_id="user-id",
            action="test",
            metadata={
                "string_val": "hello",
                "int_val": 42,
                "bool_val": True,
                "nested": {"key": "value"},
                "list_val": [1, 2, 3],
            },
        )
        assert req.metadata["int_val"] == 42
        assert req.metadata["bool_val"] is True
        assert req.metadata["nested"]["key"] == "value"


class TestActivityListResponse:
    """Verify paginated activity list response."""

    def test_activity_list_response(self):
        """ActivityListResponse wraps items with pagination metadata."""
        from schemas import ActivityResponse, ActivityListResponse

        now = datetime.now(timezone.utc)
        activities = [
            ActivityResponse(
                id=i,
                user_id="user-1",
                action=f"action-{i}",
                created_at=now,
            )
            for i in range(5)
        ]
        response = ActivityListResponse(
            items=activities, next_cursor="cursor-abc", has_more=True
        )
        assert len(response.items) == 5
        assert response.next_cursor == "cursor-abc"
        assert response.has_more is True

    def test_activity_list_empty(self):
        """Empty activity list should work."""
        from schemas import ActivityListResponse

        response = ActivityListResponse(items=[], has_more=False)
        assert response.items == []
        assert response.has_more is False


class TestActivityConfig:
    """Verify activity service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "activity-service"
        assert settings.service_port == 8023

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings

        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_redis_url_format(self):
        """redis_url property should produce a valid Redis URL."""
        from config import settings

        assert settings.redis_url.startswith("redis://")


class TestSecurityImports:
    """Verify that mobility-common security middleware is importable."""

    def test_get_current_user_import(self):
        """The get_current_user dependency should be importable."""
        from mobility_common.fastapi.middleware import get_current_user
        assert callable(get_current_user)

    def test_pagination_import(self):
        """Pagination helpers should be importable."""
        from mobility_common.fastapi.pagination import paginate, decode_cursor
        assert callable(paginate)
        assert callable(decode_cursor)
