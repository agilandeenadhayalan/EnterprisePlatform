"""
Tests for OTP service — code generation, hash verification, and schema validation.

These tests verify:
1. OTP generation produces correct format (6 numeric digits)
2. SHA-256 hash verification logic works (hash-then-compare)
3. Schema validation works correctly (Pydantic models)
4. Config loads with correct defaults

No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import hashlib
import pytest


class TestOtpGeneration:
    """Verify OTP code generation format and properties."""

    def test_otp_is_six_digits(self):
        """Generated OTP should be exactly 6 numeric digits."""
        from main import generate_otp_code

        code = generate_otp_code(6)
        assert len(code) == 6
        assert code.isdigit()

    def test_otp_respects_length_param(self):
        """OTP length should match the requested length."""
        from main import generate_otp_code

        code_4 = generate_otp_code(4)
        code_8 = generate_otp_code(8)
        assert len(code_4) == 4
        assert len(code_8) == 8
        assert code_4.isdigit()
        assert code_8.isdigit()

    def test_otp_is_zero_padded(self):
        """OTP codes like '000123' should keep leading zeros."""
        from main import generate_otp_code

        # Generate many codes and verify all are 6 chars
        for _ in range(50):
            code = generate_otp_code(6)
            assert len(code) == 6, f"Code '{code}' is not 6 digits"

    def test_otp_codes_are_different(self):
        """Two consecutive OTP codes should (almost certainly) differ."""
        from main import generate_otp_code

        code1 = generate_otp_code(6)
        code2 = generate_otp_code(6)
        # With 10^6 possibilities, collision is extremely unlikely
        # Run multiple times to be safe
        codes = {generate_otp_code(6) for _ in range(20)}
        assert len(codes) > 1, "All generated codes were identical"


class TestOtpHashing:
    """Verify SHA-256 hash-then-compare verification logic."""

    def test_hash_produces_sha256_hex(self):
        """hash_otp should produce a valid SHA-256 hex string."""
        from main import hash_otp

        hashed = hash_otp("123456")
        assert len(hashed) == 64  # SHA-256 hex is always 64 chars
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_same_code_same_hash(self):
        """Same OTP code should always produce the same hash (deterministic)."""
        from main import hash_otp

        hash1 = hash_otp("654321")
        hash2 = hash_otp("654321")
        assert hash1 == hash2

    def test_different_code_different_hash(self):
        """Different OTP codes should produce different hashes."""
        from main import hash_otp

        hash1 = hash_otp("123456")
        hash2 = hash_otp("654321")
        assert hash1 != hash2

    def test_hash_matches_stdlib_sha256(self):
        """hash_otp should match Python's standard hashlib.sha256."""
        from main import hash_otp

        code = "987654"
        expected = hashlib.sha256(code.encode("utf-8")).hexdigest()
        actual = hash_otp(code)
        assert actual == expected

    def test_verification_flow(self):
        """
        Simulate the full verification flow:
        1. Generate code
        2. Hash it (what gets stored in DB)
        3. Hash user input and compare (what verify endpoint does)
        """
        from main import generate_otp_code, hash_otp

        # Step 1: Generate
        code = generate_otp_code(6)

        # Step 2: Hash for storage
        stored_hash = hash_otp(code)

        # Step 3: User submits the same code — should match
        submitted_hash = hash_otp(code)
        assert submitted_hash == stored_hash

        # Step 4: User submits wrong code — should not match
        wrong_hash = hash_otp("000000")
        assert wrong_hash != stored_hash


class TestOtpSchemas:
    """Verify Pydantic schema validation for OTP requests/responses."""

    def test_send_otp_request_defaults(self):
        """SendOtpRequest should default to email channel and verification purpose."""
        from schemas import SendOtpRequest

        req = SendOtpRequest(user_id="user-123")
        assert req.channel == "email"
        assert req.purpose == "verification"

    def test_send_otp_request_custom_channel(self):
        """SendOtpRequest should accept custom channel and purpose."""
        from schemas import SendOtpRequest

        req = SendOtpRequest(user_id="user-123", channel="sms", purpose="login")
        assert req.channel == "sms"
        assert req.purpose == "login"

    def test_verify_otp_request_validation(self):
        """VerifyOtpRequest should enforce 6-digit code."""
        from schemas import VerifyOtpRequest

        req = VerifyOtpRequest(user_id="user-123", code="123456")
        assert req.code == "123456"

    def test_verify_otp_request_rejects_short_code(self):
        """VerifyOtpRequest should reject codes shorter than 6 digits."""
        from schemas import VerifyOtpRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VerifyOtpRequest(user_id="user-123", code="12345")

    def test_verify_otp_request_rejects_long_code(self):
        """VerifyOtpRequest should reject codes longer than 6 digits."""
        from schemas import VerifyOtpRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VerifyOtpRequest(user_id="user-123", code="1234567")

    def test_otp_status_response_no_pending(self):
        """OtpStatusResponse with no pending OTP."""
        from schemas import OtpStatusResponse

        resp = OtpStatusResponse(has_pending_otp=False)
        assert resp.has_pending_otp is False
        assert resp.channel is None

    def test_otp_status_response_with_pending(self):
        """OtpStatusResponse with a pending OTP should include details."""
        from schemas import OtpStatusResponse

        now = datetime.now(timezone.utc)
        resp = OtpStatusResponse(
            has_pending_otp=True,
            channel="email",
            purpose="verification",
            expires_at=now,
            attempts_remaining=2,
        )
        assert resp.has_pending_otp is True
        assert resp.channel == "email"
        assert resp.attempts_remaining == 2

    def test_send_otp_response(self):
        """SendOtpResponse should include channel and TTL."""
        from schemas import SendOtpResponse

        resp = SendOtpResponse(channel="sms", expires_in_minutes=10)
        assert resp.message == "OTP sent successfully"
        assert resp.expires_in_minutes == 10

    def test_verify_otp_response_success(self):
        """VerifyOtpResponse for a successful verification."""
        from schemas import VerifyOtpResponse

        resp = VerifyOtpResponse(verified=True, message="OTP verified successfully")
        assert resp.verified is True


class TestOtpConfig:
    """Verify OTP service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "otp-service"
        assert settings.service_port == 8012

    def test_otp_settings(self):
        """OTP-specific settings should have correct defaults."""
        from config import settings

        assert settings.otp_length == 6
        assert settings.otp_ttl_minutes == 10

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings

        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.postgres_db in settings.database_url
