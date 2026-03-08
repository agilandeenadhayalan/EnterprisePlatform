"""Tests for Module 02: Authentication & Authorization."""

from learning.phase_1.src.m02_authentication.auth import (
    JWTSimulator,
    RBACManager,
)


class TestJWTSimulator:
    def test_create_and_validate_token(self):
        jwt = JWTSimulator()
        result = jwt.create_token("user-1", "rider")
        payload = jwt.validate_token(result["token"])
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["role"] == "rider"

    def test_invalid_token_returns_none(self):
        jwt = JWTSimulator()
        assert jwt.validate_token("invalid.token") is None

    def test_revoked_token_is_invalid(self):
        jwt = JWTSimulator()
        result = jwt.create_token("user-1", "rider")
        jwt.revoke_token(result["jti"])
        assert jwt.validate_token(result["token"]) is None

    def test_token_pair_creates_both_types(self):
        jwt = JWTSimulator()
        pair = jwt.create_token_pair("user-1", "rider")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert pair["access_token"]["token_type"] == "access"
        assert pair["refresh_token"]["token_type"] == "refresh"


class TestRBAC:
    def test_rider_can_read_trips(self):
        rbac = RBACManager()
        assert rbac.check_access("rider", "trips", "read") is True

    def test_rider_cannot_admin_users(self):
        rbac = RBACManager()
        assert rbac.check_access("rider", "users", "admin") is False

    def test_admin_has_full_access(self):
        rbac = RBACManager()
        assert rbac.check_access("admin", "trips", "admin") is True
        assert rbac.check_access("admin", "users", "admin") is True

    def test_unknown_role_denied(self):
        rbac = RBACManager()
        assert rbac.check_access("unknown", "trips", "read") is False
