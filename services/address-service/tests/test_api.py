"""
Tests for address service — schema validation and business logic.

These tests verify:
1. AddressResponse serializes correctly
2. CreateAddressRequest validates required fields and coordinates
3. UpdateAddressRequest accepts partial updates
4. Default address flag logic
5. Config loads with correct defaults

No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestAddressSchemas:
    """Verify Pydantic schema validation for address responses."""

    def test_address_response_full(self):
        """An AddressResponse with all fields should validate."""
        from schemas import AddressResponse

        now = datetime.now(timezone.utc)
        address = AddressResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440000",
            label="home",
            line1="123 Main St",
            line2="Apt 4B",
            city="New York",
            state="NY",
            postal_code="10001",
            country="US",
            latitude=40.7128,
            longitude=-74.0060,
            is_default=True,
            created_at=now,
            updated_at=now,
        )
        assert address.label == "home"
        assert address.latitude == 40.7128
        assert address.is_default is True

    def test_address_response_optional_fields(self):
        """line2, state, postal_code, lat/lng are optional."""
        from schemas import AddressResponse

        now = datetime.now(timezone.utc)
        address = AddressResponse(
            id="test-id",
            user_id="user-id",
            label="work",
            line1="456 Office Blvd",
            city="San Francisco",
            country="US",
            is_default=False,
            created_at=now,
            updated_at=now,
        )
        assert address.line2 is None
        assert address.state is None
        assert address.latitude is None


class TestCreateAddressRequest:
    """Verify create address request validation."""

    def test_valid_create(self):
        """CreateAddressRequest with all required fields should validate."""
        from schemas import CreateAddressRequest

        req = CreateAddressRequest(
            label="home",
            line1="123 Main St",
            city="New York",
            country="US",
        )
        assert req.label == "home"
        assert req.is_default is False

    def test_create_with_coordinates(self):
        """CreateAddressRequest should accept valid coordinates."""
        from schemas import CreateAddressRequest

        req = CreateAddressRequest(
            label="office",
            line1="1 Market St",
            city="San Francisco",
            country="US",
            latitude=37.7749,
            longitude=-122.4194,
        )
        assert req.latitude == 37.7749
        assert req.longitude == -122.4194

    def test_create_invalid_latitude(self):
        """Latitude out of range should fail validation."""
        from schemas import CreateAddressRequest

        with pytest.raises(Exception):
            CreateAddressRequest(
                label="bad",
                line1="123 St",
                city="City",
                country="US",
                latitude=91.0,
            )

    def test_create_invalid_longitude(self):
        """Longitude out of range should fail validation."""
        from schemas import CreateAddressRequest

        with pytest.raises(Exception):
            CreateAddressRequest(
                label="bad",
                line1="123 St",
                city="City",
                country="US",
                longitude=-181.0,
            )

    def test_create_missing_required_fields(self):
        """Missing required fields should fail validation."""
        from schemas import CreateAddressRequest

        with pytest.raises(Exception):
            CreateAddressRequest(label="home")

    def test_label_values(self):
        """Label accepts any string up to 50 chars."""
        from schemas import CreateAddressRequest

        for label in ["home", "work", "gym", "parents"]:
            req = CreateAddressRequest(
                label=label,
                line1="123 St",
                city="City",
                country="US",
            )
            assert req.label == label

    def test_default_address_flag(self):
        """is_default defaults to False, can be set to True."""
        from schemas import CreateAddressRequest

        req_no_default = CreateAddressRequest(
            label="home", line1="123 St", city="City", country="US"
        )
        assert req_no_default.is_default is False

        req_default = CreateAddressRequest(
            label="home", line1="123 St", city="City", country="US", is_default=True
        )
        assert req_default.is_default is True


class TestUpdateAddressRequest:
    """Verify partial update request validation."""

    def test_partial_update_label_only(self):
        """Should accept just label field."""
        from schemas import UpdateAddressRequest

        req = UpdateAddressRequest(label="office")
        data = req.model_dump(exclude_unset=True)
        assert data == {"label": "office"}

    def test_partial_update_coordinates(self):
        """Should accept just coordinates."""
        from schemas import UpdateAddressRequest

        req = UpdateAddressRequest(latitude=40.0, longitude=-74.0)
        data = req.model_dump(exclude_unset=True)
        assert data == {"latitude": 40.0, "longitude": -74.0}

    def test_empty_update(self):
        """Empty update should result in no fields."""
        from schemas import UpdateAddressRequest

        req = UpdateAddressRequest()
        data = req.model_dump(exclude_unset=True)
        assert data == {}


class TestAddressConfig:
    """Verify address service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "address-service"
        assert settings.service_port == 8022

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
