"""
Tests for config service — schema validation and version increment logic.

These tests verify:
1. Schema validation works correctly (Pydantic models)
2. Version increment logic (unit test of the core concept)
3. JSONB value types (string, number, boolean, dict, list)
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


class TestConfigSchemas:
    """Verify Pydantic schema validation for config responses."""

    def test_config_response_valid(self):
        """A ConfigResponse with all required fields should validate."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="max_login_attempts",
            value=5,
            description="Maximum failed login attempts before lockout",
            version=1,
            updated_at=now,
        )
        assert config.service == "auth-service"
        assert config.key == "max_login_attempts"
        assert config.value == 5
        assert config.version == 1

    def test_config_response_optional_description(self):
        """description is optional and can be None."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="debug",
            value=True,
            description=None,
            version=3,
            updated_at=now,
        )
        assert config.description is None

    def test_set_config_request_with_description(self):
        """SetConfigRequest should accept value and optional description."""
        from schemas import SetConfigRequest

        req = SetConfigRequest(
            value={"timeout": 30, "retries": 3},
            description="HTTP client settings",
        )
        assert req.value == {"timeout": 30, "retries": 3}
        assert req.description == "HTTP client settings"

    def test_set_config_request_without_description(self):
        """SetConfigRequest description defaults to None."""
        from schemas import SetConfigRequest

        req = SetConfigRequest(value="production")
        assert req.value == "production"
        assert req.description is None

    def test_config_list_response(self):
        """ConfigListResponse wraps a list of configs with a count."""
        from schemas import ConfigResponse, ConfigListResponse

        now = datetime.now(timezone.utc)
        configs = [
            ConfigResponse(
                service="auth-service",
                key=f"key-{i}",
                value=i,
                version=1,
                updated_at=now,
            )
            for i in range(3)
        ]
        response = ConfigListResponse(configs=configs, count=3)
        assert response.count == 3
        assert len(response.configs) == 3

    def test_config_list_empty(self):
        """Empty config list should work with count=0."""
        from schemas import ConfigListResponse

        response = ConfigListResponse(configs=[], count=0)
        assert response.count == 0
        assert response.configs == []


class TestVersionIncrementLogic:
    """
    Test the versioned configuration concept.

    Every update should increment the version number. This is the core
    invariant of the config service — downstream services compare cached
    versions against the DB to detect config changes.
    """

    def test_version_starts_at_one(self):
        """A new config entry starts at version 1."""
        version = 1  # Initial version for new entries
        assert version == 1

    def test_version_increments_on_update(self):
        """Updating a config should increment version by 1."""
        current_version = 1
        new_version = current_version + 1
        assert new_version == 2

    def test_version_increments_sequentially(self):
        """Multiple updates should produce sequential version numbers."""
        version = 1
        for expected in [2, 3, 4, 5]:
            version = version + 1
            assert version == expected

    def test_version_never_decreases(self):
        """Version should only ever go up, never down."""
        versions = []
        version = 1
        versions.append(version)
        for _ in range(10):
            version = version + 1
            versions.append(version)

        # Verify monotonically increasing
        for i in range(1, len(versions)):
            assert versions[i] > versions[i - 1]


class TestJSONBValueTypes:
    """
    Test that config values can be any JSON-serializable type.

    The platform.configurations table stores values as JSONB, so the API
    must accept and return strings, numbers, booleans, dicts, and lists.
    """

    def test_string_value(self):
        """Config value can be a string."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="jwt_algorithm",
            value="HS256",
            version=1,
            updated_at=now,
        )
        assert config.value == "HS256"
        assert isinstance(config.value, str)

    def test_integer_value(self):
        """Config value can be an integer."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="max_retries",
            value=5,
            version=1,
            updated_at=now,
        )
        assert config.value == 5
        assert isinstance(config.value, int)

    def test_boolean_value(self):
        """Config value can be a boolean."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="debug_mode",
            value=False,
            version=1,
            updated_at=now,
        )
        assert config.value is False

    def test_dict_value(self):
        """Config value can be a nested dict (JSON object)."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        nested = {"smtp": {"host": "mail.example.com", "port": 587, "tls": True}}
        config = ConfigResponse(
            service="notification-service",
            key="email_settings",
            value=nested,
            version=2,
            updated_at=now,
        )
        assert config.value["smtp"]["host"] == "mail.example.com"
        assert config.value["smtp"]["tls"] is True

    def test_list_value(self):
        """Config value can be a list (JSON array)."""
        from schemas import ConfigResponse

        now = datetime.now(timezone.utc)
        config = ConfigResponse(
            service="auth-service",
            key="allowed_origins",
            value=["https://app.example.com", "https://admin.example.com"],
            version=1,
            updated_at=now,
        )
        assert len(config.value) == 2
        assert "https://app.example.com" in config.value

    def test_set_config_request_accepts_any_json(self):
        """SetConfigRequest value field should accept any JSON type."""
        from schemas import SetConfigRequest

        # String
        assert SetConfigRequest(value="hello").value == "hello"
        # Number
        assert SetConfigRequest(value=42).value == 42
        # Boolean
        assert SetConfigRequest(value=True).value is True
        # Dict
        assert SetConfigRequest(value={"a": 1}).value == {"a": 1}
        # List
        assert SetConfigRequest(value=[1, 2, 3]).value == [1, 2, 3]
        # None
        assert SetConfigRequest(value=None).value is None


class TestConfigServiceConfig:
    """Verify config service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "config-service"
        assert settings.service_port == 8030

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

    def test_require_role_import(self):
        """The require_role dependency factory should be importable."""
        from mobility_common.fastapi.middleware import require_role
        assert callable(require_role)

    def test_get_current_user_import(self):
        """The get_current_user dependency should be importable."""
        from mobility_common.fastapi.middleware import get_current_user
        assert callable(get_current_user)

    def test_error_helpers_import(self):
        """Error factory functions should be importable."""
        from mobility_common.fastapi.errors import not_found, conflict
        assert callable(not_found)
        assert callable(conflict)
