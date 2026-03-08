"""
Tests for user service — schema validation and business logic.

These tests verify:
1. UserResponse serializes correctly
2. UpdateUserRequest accepts partial updates
3. UserListResponse wraps paginated data
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


class TestUserSchemas:
    """Verify Pydantic schema validation for user responses."""

    def test_user_response_valid(self):
        """A UserResponse with all required fields should validate."""
        from schemas import UserResponse

        now = datetime.now(timezone.utc)
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="alice@example.com",
            full_name="Alice Smith",
            role="rider",
            phone="+1234567890",
            is_active=True,
            is_verified=True,
            created_at=now,
        )
        assert user.id == "550e8400-e29b-41d4-a716-446655440000"
        assert user.email == "alice@example.com"
        assert user.role == "rider"

    def test_user_response_optional_phone(self):
        """Phone is optional and defaults to None."""
        from schemas import UserResponse

        now = datetime.now(timezone.utc)
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="bob@example.com",
            full_name="Bob Jones",
            role="admin",
            is_active=True,
            is_verified=False,
            created_at=now,
        )
        assert user.phone is None

    def test_user_response_serialization(self):
        """UserResponse should serialize to dict with all fields."""
        from schemas import UserResponse

        now = datetime.now(timezone.utc)
        user = UserResponse(
            id="test-id",
            email="test@test.com",
            full_name="Test User",
            role="rider",
            phone=None,
            is_active=True,
            is_verified=False,
            created_at=now,
        )
        data = user.model_dump()
        assert "id" in data
        assert "email" in data
        assert "password_hash" not in data  # Never exposed


class TestUpdateUserRequest:
    """Verify partial update schema validation."""

    def test_all_fields_optional(self):
        """UpdateUserRequest should accept no fields (empty update)."""
        from schemas import UpdateUserRequest

        req = UpdateUserRequest()
        assert req.full_name is None
        assert req.phone is None
        assert req.email is None

    def test_partial_update_name_only(self):
        """Should accept just full_name."""
        from schemas import UpdateUserRequest

        req = UpdateUserRequest(full_name="New Name")
        data = req.model_dump(exclude_unset=True)
        assert data == {"full_name": "New Name"}
        assert "phone" not in data
        assert "email" not in data

    def test_partial_update_phone_only(self):
        """Should accept just phone."""
        from schemas import UpdateUserRequest

        req = UpdateUserRequest(phone="+9876543210")
        data = req.model_dump(exclude_unset=True)
        assert data == {"phone": "+9876543210"}

    def test_partial_update_multiple_fields(self):
        """Should accept multiple fields at once."""
        from schemas import UpdateUserRequest

        req = UpdateUserRequest(full_name="Updated", email="new@example.com")
        data = req.model_dump(exclude_unset=True)
        assert data == {"full_name": "Updated", "email": "new@example.com"}

    def test_full_name_min_length(self):
        """full_name must be at least 1 character."""
        from schemas import UpdateUserRequest

        with pytest.raises(Exception):
            UpdateUserRequest(full_name="")


class TestUserListResponse:
    """Verify paginated user list response."""

    def test_user_list_response(self):
        """UserListResponse wraps items with pagination metadata."""
        from schemas import UserResponse, UserListResponse

        now = datetime.now(timezone.utc)
        users = [
            UserResponse(
                id=f"id-{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                role="rider",
                is_active=True,
                is_verified=True,
                created_at=now,
            )
            for i in range(3)
        ]
        response = UserListResponse(items=users, next_cursor="abc", has_more=True)
        assert len(response.items) == 3
        assert response.next_cursor == "abc"
        assert response.has_more is True

    def test_user_list_empty(self):
        """Empty user list should work."""
        from schemas import UserListResponse

        response = UserListResponse(items=[], has_more=False)
        assert response.items == []
        assert response.has_more is False
        assert response.next_cursor is None


class TestUserConfig:
    """Verify user service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "user-service"
        assert settings.service_port == 8020

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings

        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.postgres_db in settings.database_url

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

    def test_require_role_import(self):
        """The require_role dependency should be importable."""
        from mobility_common.fastapi.middleware import require_role
        assert callable(require_role)

    def test_pagination_import(self):
        """Pagination helpers should be importable."""
        from mobility_common.fastapi.pagination import paginate, decode_cursor
        assert callable(paginate)
        assert callable(decode_cursor)
