"""
Tests for profile service — schema validation and partial update logic.

These tests verify:
1. ProfileResponse serializes correctly
2. CreateProfileRequest and UpdateProfileRequest accept all-optional fields
3. Partial update only includes set fields
4. Config loads with correct defaults

No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timezone

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestProfileSchemas:
    """Verify Pydantic schema validation for profile responses."""

    def test_profile_response_full(self):
        """A ProfileResponse with all fields should validate."""
        from schemas import ProfileResponse

        now = datetime.now(timezone.utc)
        profile = ProfileResponse(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            avatar_url="https://cdn.example.com/avatar.jpg",
            bio="Software engineer and cyclist",
            date_of_birth=date(1990, 5, 15),
            language="en",
            timezone="America/New_York",
            created_at=now,
            updated_at=now,
        )
        assert profile.user_id == "550e8400-e29b-41d4-a716-446655440000"
        assert profile.language == "en"

    def test_profile_response_minimal(self):
        """ProfileResponse with only user_id (all optional fields None)."""
        from schemas import ProfileResponse

        profile = ProfileResponse(user_id="test-id")
        assert profile.user_id == "test-id"
        assert profile.avatar_url is None
        assert profile.bio is None
        assert profile.date_of_birth is None

    def test_profile_response_serialization(self):
        """ProfileResponse should serialize to dict."""
        from schemas import ProfileResponse

        profile = ProfileResponse(
            user_id="test-id",
            language="fr",
            timezone="Europe/Paris",
        )
        data = profile.model_dump()
        assert data["language"] == "fr"
        assert data["timezone"] == "Europe/Paris"


class TestCreateProfileRequest:
    """Verify create profile request validation."""

    def test_all_fields_optional(self):
        """CreateProfileRequest should accept no fields."""
        from schemas import CreateProfileRequest

        req = CreateProfileRequest()
        assert req.avatar_url is None
        assert req.bio is None

    def test_full_create(self):
        """CreateProfileRequest with all fields set."""
        from schemas import CreateProfileRequest

        req = CreateProfileRequest(
            avatar_url="https://cdn.example.com/photo.jpg",
            bio="A short bio",
            date_of_birth=date(1995, 3, 20),
            language="es",
            timezone="America/Mexico_City",
        )
        assert req.language == "es"
        assert req.date_of_birth == date(1995, 3, 20)


class TestUpdateProfileRequest:
    """Verify partial update request validation."""

    def test_partial_update_bio_only(self):
        """Should accept just bio field."""
        from schemas import UpdateProfileRequest

        req = UpdateProfileRequest(bio="Updated bio")
        data = req.model_dump(exclude_unset=True)
        assert data == {"bio": "Updated bio"}
        assert "avatar_url" not in data

    def test_partial_update_language_and_timezone(self):
        """Should accept language and timezone together."""
        from schemas import UpdateProfileRequest

        req = UpdateProfileRequest(language="de", timezone="Europe/Berlin")
        data = req.model_dump(exclude_unset=True)
        assert data == {"language": "de", "timezone": "Europe/Berlin"}

    def test_empty_update(self):
        """Empty UpdateProfileRequest should result in no fields."""
        from schemas import UpdateProfileRequest

        req = UpdateProfileRequest()
        data = req.model_dump(exclude_unset=True)
        assert data == {}

    def test_bio_max_length(self):
        """Bio exceeding max length should fail validation."""
        from schemas import UpdateProfileRequest

        with pytest.raises(Exception):
            UpdateProfileRequest(bio="x" * 2001)


class TestProfileConfig:
    """Verify profile service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "profile-service"
        assert settings.service_port == 8021

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

    def test_error_helpers_import(self):
        """Error factory functions should be importable."""
        from mobility_common.fastapi.errors import not_found, forbidden
        assert callable(not_found)
        assert callable(forbidden)
