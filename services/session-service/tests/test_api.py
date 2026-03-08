"""
Tests for session service — schema validation and security module imports.

These tests verify:
1. Schema validation works correctly (Pydantic models)
2. Security module imports resolve (mobility-common middleware)
3. Config loads with correct defaults

No database needed — these are unit tests with mocked dependencies.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestSessionSchemas:
    """Verify Pydantic schema validation for session responses."""

    def test_session_response_valid(self):
        """A SessionResponse with all required fields should validate."""
        from schemas import SessionResponse

        now = datetime.now(timezone.utc)
        session = SessionResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440000",
            device_info={"browser": "Chrome", "os": "Windows"},
            ip_address="192.168.1.1",
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        assert session.id == "550e8400-e29b-41d4-a716-446655440000"
        assert session.device_info["browser"] == "Chrome"

    def test_session_response_optional_fields(self):
        """device_info and ip_address are optional (nullable in DB)."""
        from schemas import SessionResponse

        now = datetime.now(timezone.utc)
        session = SessionResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440000",
            device_info=None,
            ip_address=None,
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        assert session.device_info is None
        assert session.ip_address is None

    def test_session_list_response(self):
        """SessionListResponse wraps a list of sessions with a count."""
        from schemas import SessionResponse, SessionListResponse

        now = datetime.now(timezone.utc)
        sessions = [
            SessionResponse(
                id=f"id-{i}",
                user_id="user-1",
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
            for i in range(3)
        ]
        response = SessionListResponse(sessions=sessions, count=3)
        assert response.count == 3
        assert len(response.sessions) == 3

    def test_session_count_response(self):
        """SessionCountResponse holds an integer count."""
        from schemas import SessionCountResponse

        response = SessionCountResponse(active_count=5)
        assert response.active_count == 5

    def test_session_list_empty(self):
        """Empty session list should work with count=0."""
        from schemas import SessionListResponse

        response = SessionListResponse(sessions=[], count=0)
        assert response.count == 0
        assert response.sessions == []


class TestSecurityImports:
    """Verify that mobility-common security middleware is importable."""

    def test_get_current_user_import(self):
        """The get_current_user dependency should be importable."""
        from mobility_common.fastapi.middleware import get_current_user
        assert callable(get_current_user)

    def test_token_payload_import(self):
        """TokenPayload schema should be importable and instantiable."""
        from mobility_common.fastapi.middleware import TokenPayload

        payload = TokenPayload(
            sub="user-123",
            email="test@test.com",
            role="rider",
            exp=9999999999,
            iat=1000000000,
        )
        assert payload.sub == "user-123"
        assert payload.role == "rider"

    def test_error_helpers_import(self):
        """Error factory functions should be importable."""
        from mobility_common.fastapi.errors import not_found, forbidden
        assert callable(not_found)
        assert callable(forbidden)


class TestSessionConfig:
    """Verify session service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "session-service"
        assert settings.service_port == 8011

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings

        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.postgres_db in settings.database_url

    def test_redis_url_format(self):
        """redis_url property should produce a valid Redis URL."""
        from config import settings

        assert settings.redis_url.startswith("redis://")
