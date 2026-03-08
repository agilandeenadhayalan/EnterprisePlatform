"""
Tests for preferences service — schema validation and JSONB value types.

These tests verify:
1. PreferenceResponse serializes correctly
2. SetPreferenceRequest accepts various JSONB value types (string, int, bool, dict)
3. PreferenceListResponse wraps grouped preferences
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


class TestPreferenceSchemas:
    """Verify Pydantic schema validation for preference responses."""

    def test_preference_response_string_value(self):
        """PreferenceResponse with a string value."""
        from schemas import PreferenceResponse

        now = datetime.now(timezone.utc)
        pref = PreferenceResponse(
            category="notifications",
            key="email_frequency",
            value="daily",
            updated_at=now,
        )
        assert pref.category == "notifications"
        assert pref.key == "email_frequency"
        assert pref.value == "daily"

    def test_preference_response_int_value(self):
        """PreferenceResponse with an integer value."""
        from schemas import PreferenceResponse

        pref = PreferenceResponse(
            category="ride",
            key="auto_tip_percent",
            value=15,
        )
        assert pref.value == 15

    def test_preference_response_bool_value(self):
        """PreferenceResponse with a boolean value."""
        from schemas import PreferenceResponse

        pref = PreferenceResponse(
            category="notifications",
            key="push_enabled",
            value=True,
        )
        assert pref.value is True

    def test_preference_response_dict_value(self):
        """PreferenceResponse with a dict/object value."""
        from schemas import PreferenceResponse

        pref = PreferenceResponse(
            category="display",
            key="map_settings",
            value={"zoom": 14, "style": "dark", "traffic": True},
        )
        assert pref.value["zoom"] == 14
        assert pref.value["style"] == "dark"

    def test_preference_response_null_value(self):
        """PreferenceResponse with None value."""
        from schemas import PreferenceResponse

        pref = PreferenceResponse(
            category="ride",
            key="default_vehicle",
            value=None,
        )
        assert pref.value is None

    def test_preference_serialization(self):
        """PreferenceResponse should serialize to dict."""
        from schemas import PreferenceResponse

        pref = PreferenceResponse(
            category="display",
            key="theme",
            value="dark",
        )
        data = pref.model_dump()
        assert data["category"] == "display"
        assert data["key"] == "theme"
        assert data["value"] == "dark"


class TestSetPreferenceRequest:
    """Verify set preference request validation."""

    def test_set_string_value(self):
        """SetPreferenceRequest should accept string values."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value="en")
        assert req.value == "en"

    def test_set_int_value(self):
        """SetPreferenceRequest should accept integer values."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value=20)
        assert req.value == 20

    def test_set_bool_value(self):
        """SetPreferenceRequest should accept boolean values."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value=False)
        assert req.value is False

    def test_set_dict_value(self):
        """SetPreferenceRequest should accept dict values."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value={"key": "val", "num": 42})
        assert req.value["key"] == "val"
        assert req.value["num"] == 42

    def test_set_list_value(self):
        """SetPreferenceRequest should accept list values."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value=["a", "b", "c"])
        assert req.value == ["a", "b", "c"]

    def test_set_null_value(self):
        """SetPreferenceRequest should accept None to clear a preference."""
        from schemas import SetPreferenceRequest

        req = SetPreferenceRequest(value=None)
        assert req.value is None


class TestPreferenceListResponse:
    """Verify preference list response."""

    def test_preference_list(self):
        """PreferenceListResponse wraps a list of preferences."""
        from schemas import PreferenceResponse, PreferenceListResponse

        prefs = [
            PreferenceResponse(category="notifications", key="push_enabled", value=True),
            PreferenceResponse(category="notifications", key="email_enabled", value=False),
            PreferenceResponse(category="ride", key="auto_tip_percent", value=15),
        ]
        response = PreferenceListResponse(user_id="user-123", preferences=prefs)
        assert response.user_id == "user-123"
        assert len(response.preferences) == 3

    def test_preference_list_empty(self):
        """Empty preference list should work."""
        from schemas import PreferenceListResponse

        response = PreferenceListResponse(user_id="user-123", preferences=[])
        assert response.preferences == []


class TestPreferencesConfig:
    """Verify preferences service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "preferences-service"
        assert settings.service_port == 8024

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
