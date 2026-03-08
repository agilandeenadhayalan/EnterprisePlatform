"""
Tests for the access-control service.

Tests permission checking logic — creates sample roles with permissions JSONB,
and verifies that check_permission correctly matches wildcards (e.g., "user:*"
matches "user:read").
"""

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import fnmatch
import pytest

from schemas import (
    CheckPermissionRequest,
    CheckPermissionResponse,
    RoleResponse,
    AssignRoleRequest,
    UserRoleResponse,
)


# -- Unit tests for wildcard permission matching --

def _match_permission(permission: str, role_permissions: list[str]) -> bool:
    """
    Replicate the permission matching logic from the repository.

    This is the core algorithm: iterate over a role's permission patterns
    and use fnmatch to do glob-style matching. "user:*" matches "user:read",
    "user:write", "user:delete", etc.
    """
    for pattern in role_permissions:
        if fnmatch.fnmatch(permission, pattern):
            return True
    return False


class TestWildcardPermissionMatching:
    """Test that wildcard patterns in role permissions match correctly."""

    def test_exact_match(self):
        """Exact permission string should match."""
        perms = ["user:read", "user:write", "ride:create"]
        assert _match_permission("user:read", perms) is True

    def test_exact_no_match(self):
        """Permission not in the list should not match."""
        perms = ["user:read", "user:write"]
        assert _match_permission("ride:create", perms) is False

    def test_wildcard_matches_specific(self):
        """'user:*' should match 'user:read', 'user:write', etc."""
        perms = ["user:*"]
        assert _match_permission("user:read", perms) is True
        assert _match_permission("user:write", perms) is True
        assert _match_permission("user:delete", perms) is True

    def test_wildcard_does_not_cross_domains(self):
        """'user:*' should NOT match 'ride:read'."""
        perms = ["user:*"]
        assert _match_permission("ride:read", perms) is False

    def test_full_wildcard(self):
        """'*' should match everything (super-admin)."""
        perms = ["*"]
        assert _match_permission("user:read", perms) is True
        assert _match_permission("ride:delete", perms) is True
        assert _match_permission("admin:manage", perms) is True

    def test_multiple_wildcard_patterns(self):
        """Multiple wildcard patterns should all be checked."""
        perms = ["user:*", "ride:read"]
        assert _match_permission("user:write", perms) is True
        assert _match_permission("ride:read", perms) is True
        assert _match_permission("ride:write", perms) is False

    def test_empty_permissions(self):
        """Empty permissions list should match nothing."""
        assert _match_permission("user:read", []) is False

    def test_nested_wildcard(self):
        """'user:profile:*' should match 'user:profile:read'."""
        perms = ["user:profile:*"]
        assert _match_permission("user:profile:read", perms) is True
        assert _match_permission("user:profile:write", perms) is True
        assert _match_permission("user:settings:read", perms) is False


class TestSchemaValidation:
    """Test that Pydantic schemas validate correctly."""

    def test_check_permission_request_valid(self):
        """Valid CheckPermissionRequest should parse correctly."""
        req = CheckPermissionRequest(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            permission="user:read",
        )
        assert req.user_id == "550e8400-e29b-41d4-a716-446655440000"
        assert req.permission == "user:read"

    def test_check_permission_response_allowed(self):
        """Allowed response should include role and permissions."""
        resp = CheckPermissionResponse(
            allowed=True,
            role="admin",
            permissions=["user:*", "ride:*"],
        )
        assert resp.allowed is True
        assert resp.role == "admin"
        assert "user:*" in resp.permissions

    def test_check_permission_response_denied(self):
        """Denied response should have no role and empty permissions."""
        resp = CheckPermissionResponse(
            allowed=False,
            role=None,
            permissions=[],
        )
        assert resp.allowed is False
        assert resp.role is None

    def test_role_response_schema(self):
        """RoleResponse should accept all required fields."""
        from datetime import datetime
        role = RoleResponse(
            id="123",
            name="admin",
            description="Full access",
            permissions=["*"],
            is_system=True,
            created_at=datetime.utcnow(),
        )
        assert role.name == "admin"
        assert role.is_system is True

    def test_assign_role_request(self):
        """AssignRoleRequest should require role_id."""
        req = AssignRoleRequest(role_id="abc-123")
        assert req.role_id == "abc-123"
