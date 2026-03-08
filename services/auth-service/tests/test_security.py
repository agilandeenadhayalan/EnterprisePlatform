"""
Tests for password hashing and JWT token creation.

These tests verify the core security functions without needing
a database or HTTP server — pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import jwt
import pytest

# Need to reference as module name matches directory
import security
import config


class TestPasswordHashing:
    """Verify bcrypt password hashing behavior."""

    def test_hash_produces_bcrypt_format(self):
        """Bcrypt hashes start with $2b$ and include the cost factor."""
        hashed = security.hash_password("test_password")
        assert hashed.startswith("$2b$")
        assert f"${config.settings.bcrypt_rounds}$" in hashed

    def test_same_password_different_hashes(self):
        """Each hash uses a random salt, so same password → different hashes."""
        hash1 = security.hash_password("same_password")
        hash2 = security.hash_password("same_password")
        assert hash1 != hash2  # Different salts

    def test_verify_correct_password(self):
        """Correct password should verify True."""
        hashed = security.hash_password("correct_password")
        assert security.verify_password("correct_password", hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password should verify False."""
        hashed = security.hash_password("correct_password")
        assert security.verify_password("wrong_password", hashed) is False

    def test_hash_is_deterministic_length(self):
        """Bcrypt hashes are always 60 characters."""
        hashed = security.hash_password("any_password")
        assert len(hashed) == 60


class TestJWTTokens:
    """Verify JWT token creation and structure."""

    def test_access_token_contains_required_claims(self):
        """Access token must include sub, email, role, exp, iat, jti."""
        token, expires_in = security.create_access_token(
            user_id="user-123",
            email="test@test.com",
            role="rider",
        )
        payload = jwt.decode(
            token, config.settings.jwt_secret_key,
            algorithms=[config.settings.jwt_algorithm],
        )
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@test.com"
        assert payload["role"] == "rider"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_access_token_expires_in_correct_ttl(self):
        """expires_in should match the configured TTL."""
        _, expires_in = security.create_access_token("u", "e@e.com", "rider")
        expected = config.settings.jwt_access_token_ttl_minutes * 60
        assert expires_in == expected

    def test_refresh_token_is_different_type(self):
        """Refresh tokens have type='refresh' to prevent misuse."""
        token, _ = security.create_refresh_token("user-123")
        payload = jwt.decode(
            token, config.settings.jwt_secret_key,
            algorithms=[config.settings.jwt_algorithm],
        )
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-123"

    def test_token_pair_returns_both_tokens(self):
        """create_token_pair returns access + refresh + metadata."""
        pair = security.create_token_pair("user-123", "test@test.com", "rider")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert pair["token_type"] == "bearer"
        assert pair["expires_in"] > 0

    def test_each_token_has_unique_jti(self):
        """Every token gets a unique JTI for revocation tracking."""
        pair1 = security.create_token_pair("u", "e@e.com", "rider")
        pair2 = security.create_token_pair("u", "e@e.com", "rider")

        p1 = jwt.decode(pair1["access_token"], config.settings.jwt_secret_key,
                        algorithms=[config.settings.jwt_algorithm])
        p2 = jwt.decode(pair2["access_token"], config.settings.jwt_secret_key,
                        algorithms=[config.settings.jwt_algorithm])
        assert p1["jti"] != p2["jti"]
