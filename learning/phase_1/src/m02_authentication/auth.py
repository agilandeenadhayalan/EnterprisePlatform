"""
Authentication & Authorization Simulator
=========================================

Demonstrates JWT token lifecycle, RBAC, and session management
without external dependencies (no real cryptography — educational only).

Architecture:
    Login → Issue JWT (access + refresh) → Validate → Refresh → Revoke
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── JWT Simulator ──


@dataclass
class JWTConfig:
    """JWT configuration."""
    secret_key: str = "mobility-platform-secret-key-change-me"
    access_token_ttl: int = 900      # 15 minutes
    refresh_token_ttl: int = 604800  # 7 days
    issuer: str = "mobility-platform"


class JWTSimulator:
    """
    Simplified JWT implementation for learning purposes.

    WHY JWT over sessions:
    - Stateless: No server-side session storage needed (scales horizontally)
    - Self-contained: Token carries user claims (role, permissions)
    - Standard: Interoperable across services (each service validates independently)

    TRADE-OFF: JWTs can't be revoked without a blacklist (we implement one below).
    Session tokens are simpler but require shared storage (Redis).
    """

    def __init__(self, config: JWTConfig | None = None) -> None:
        self.config = config or JWTConfig()
        self.revoked_tokens: set[str] = set()  # Token blacklist

    def create_token(self, user_id: str, role: str, token_type: str = "access") -> dict:
        """
        Create a JWT-like token (simplified — real JWT uses RS256/ES256).

        Returns dict with 'token' string and 'expires_at' timestamp.
        """
        now = int(time.time())
        ttl = (self.config.access_token_ttl if token_type == "access"
               else self.config.refresh_token_ttl)

        payload = {
            "sub": user_id,
            "role": role,
            "type": token_type,
            "iat": now,
            "exp": now + ttl,
            "iss": self.config.issuer,
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
        }

        # Simplified "signing" (real JWT uses HMAC-SHA256 or RSA)
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode()

        signature = hmac.new(
            self.config.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]

        token = f"{payload_b64}.{signature}"

        return {
            "token": token,
            "expires_at": now + ttl,
            "token_type": token_type,
            "jti": payload["jti"],
        }

    def validate_token(self, token: str) -> dict | None:
        """Validate and decode a token. Returns payload or None."""
        try:
            payload_b64, signature = token.rsplit(".", 1)

            # Verify signature
            expected_sig = hmac.new(
                self.config.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256,
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_sig):
                return None

            # Decode payload
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))

            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None

            # Check revocation
            if payload.get("jti") in self.revoked_tokens:
                return None

            return payload

        except Exception:
            return None

    def revoke_token(self, jti: str) -> None:
        """Add a token ID to the revocation blacklist."""
        self.revoked_tokens.add(jti)

    def create_token_pair(self, user_id: str, role: str) -> dict:
        """Create both access and refresh tokens."""
        access = self.create_token(user_id, role, "access")
        refresh = self.create_token(user_id, role, "refresh")
        return {"access_token": access, "refresh_token": refresh}


# ── RBAC ──


@dataclass
class Permission:
    """A permission grants access to a specific resource+action."""
    resource: str   # e.g., "trips", "users", "drivers"
    action: str     # e.g., "read", "write", "delete", "admin"


@dataclass
class Role:
    """A role is a named collection of permissions."""
    name: str
    permissions: list[Permission] = field(default_factory=list)

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if this role has a specific permission."""
        return any(
            p.resource == resource and (p.action == action or p.action == "admin")
            for p in self.permissions
        )


class RBACManager:
    """
    Role-Based Access Control manager.

    WHY RBAC:
    - Scalable: Add permissions to roles, not individual users
    - Auditable: Clear mapping of who can do what
    - Standard: Well-understood pattern for enterprise applications

    In the mobility platform, roles include: rider, driver, admin, support.
    """

    def __init__(self) -> None:
        self.roles: dict[str, Role] = {}
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        """Create default platform roles."""
        self.roles["rider"] = Role("rider", [
            Permission("trips", "read"),
            Permission("trips", "write"),  # Can request rides
            Permission("profile", "read"),
            Permission("profile", "write"),
        ])

        self.roles["driver"] = Role("driver", [
            Permission("trips", "read"),
            Permission("driver_profile", "read"),
            Permission("driver_profile", "write"),
            Permission("location", "write"),  # Can update GPS location
        ])

        self.roles["admin"] = Role("admin", [
            Permission("trips", "admin"),
            Permission("users", "admin"),
            Permission("drivers", "admin"),
            Permission("config", "admin"),
        ])

    def check_access(self, role_name: str, resource: str, action: str) -> bool:
        """Check if a role has access to perform an action on a resource."""
        role = self.roles.get(role_name)
        if not role:
            return False
        return role.has_permission(resource, action)
