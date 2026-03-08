"""
Tests for the device service.

Tests device registration schema validation and trust toggling logic.
"""

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas import (
    RegisterDeviceRequest,
    TrustDeviceRequest,
    DeviceResponse,
)


class TestRegisterDeviceSchema:
    """Test RegisterDeviceRequest validation."""

    def test_valid_registration(self):
        """All fields provided should parse correctly."""
        req = RegisterDeviceRequest(
            device_id="device-abc-123",
            device_name="Chrome on MacBook",
            device_type="desktop",
            os="macOS 14.2",
            browser="Chrome 120",
            fingerprint="sha256:abcdef1234567890",
        )
        assert req.device_id == "device-abc-123"
        assert req.device_name == "Chrome on MacBook"
        assert req.device_type == "desktop"

    def test_minimal_registration(self):
        """Only required fields should be enough."""
        req = RegisterDeviceRequest(
            device_id="device-456",
            device_name="My Phone",
        )
        assert req.device_id == "device-456"
        assert req.device_name == "My Phone"
        assert req.os is None
        assert req.browser is None

    def test_missing_device_id_fails(self):
        """device_id is required."""
        with pytest.raises(ValidationError):
            RegisterDeviceRequest(device_name="Test Device")

    def test_missing_device_name_fails(self):
        """device_name is required."""
        with pytest.raises(ValidationError):
            RegisterDeviceRequest(device_id="device-789")

    def test_device_name_max_length(self):
        """device_name must be at most 255 characters."""
        with pytest.raises(ValidationError):
            RegisterDeviceRequest(
                device_id="device-001",
                device_name="x" * 256,
            )

    def test_device_type_max_length(self):
        """device_type must be at most 50 characters."""
        with pytest.raises(ValidationError):
            RegisterDeviceRequest(
                device_id="device-001",
                device_name="Test",
                device_type="x" * 51,
            )


class TestTrustDeviceSchema:
    """Test TrustDeviceRequest validation."""

    def test_trust_true(self):
        """Setting is_trusted to True should work."""
        req = TrustDeviceRequest(is_trusted=True)
        assert req.is_trusted is True

    def test_trust_false(self):
        """Setting is_trusted to False should work."""
        req = TrustDeviceRequest(is_trusted=False)
        assert req.is_trusted is False

    def test_missing_is_trusted_fails(self):
        """is_trusted is required."""
        with pytest.raises(ValidationError):
            TrustDeviceRequest()


class TestDeviceResponseSchema:
    """Test DeviceResponse output shape."""

    def test_full_response(self):
        """DeviceResponse should accept all fields."""
        resp = DeviceResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440001",
            device_id="device-abc",
            device_name="Chrome on MacBook",
            device_type="desktop",
            os="macOS 14.2",
            browser="Chrome 120",
            fingerprint="sha256:abc123",
            is_trusted=True,
            last_used_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        assert resp.is_trusted is True
        assert resp.device_name == "Chrome on MacBook"

    def test_minimal_response(self):
        """DeviceResponse with only required fields."""
        resp = DeviceResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440001",
            device_id="device-xyz",
            created_at=datetime.utcnow(),
        )
        assert resp.is_trusted is False
        assert resp.device_name is None
        assert resp.os is None

    def test_trust_toggle_logic(self):
        """Simulate trust toggle: device starts untrusted, gets trusted."""
        device_data = {
            "id": "aaa",
            "user_id": "bbb",
            "device_id": "dev-1",
            "device_name": "Test",
            "is_trusted": False,
            "created_at": datetime.utcnow(),
        }
        # Initially untrusted
        resp1 = DeviceResponse(**device_data)
        assert resp1.is_trusted is False

        # After trust update
        device_data["is_trusted"] = True
        resp2 = DeviceResponse(**device_data)
        assert resp2.is_trusted is True

        # Untrust again
        device_data["is_trusted"] = False
        resp3 = DeviceResponse(**device_data)
        assert resp3.is_trusted is False
