"""
Demo: Authentication & Authorization
=====================================

Run: python -m learning.phase_1.src.m02_authentication.demo
"""

from .auth import JWTSimulator, RBACManager


def demo_jwt_lifecycle() -> None:
    """Demonstrate JWT token creation, validation, and revocation."""
    print("\n+------------------------------------------+")
    print("|   Demo: JWT Token Lifecycle              |")
    print("+------------------------------------------+\n")

    jwt = JWTSimulator()

    # Create token pair
    tokens = jwt.create_token_pair("user-123", "rider")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    print(f"  Access token:  ...{access['token'][-20:]}")
    print(f"  Refresh token: ...{refresh['token'][-20:]}")
    print(f"  Access TTL:    {access['expires_at'] - __import__('time').time():.0f}s")
    print(f"  Refresh TTL:   {refresh['expires_at'] - __import__('time').time():.0f}s")

    # Validate
    payload = jwt.validate_token(access["token"])
    print(f"\n  Validated: sub={payload['sub']}, role={payload['role']}, type={payload['type']}")

    # Revoke
    jwt.revoke_token(access["jti"])
    result = jwt.validate_token(access["token"])
    print(f"  After revocation: {'valid' if result else 'REVOKED [FAIL]'}")


def demo_rbac() -> None:
    """Demonstrate Role-Based Access Control."""
    print("\n+------------------------------------------+")
    print("|   Demo: Role-Based Access Control        |")
    print("+------------------------------------------+\n")

    rbac = RBACManager()

    checks = [
        ("rider", "trips", "read"),
        ("rider", "trips", "write"),
        ("rider", "users", "admin"),
        ("driver", "location", "write"),
        ("driver", "config", "admin"),
        ("admin", "trips", "admin"),
        ("admin", "users", "admin"),
    ]

    for role, resource, action in checks:
        allowed = rbac.check_access(role, resource, action)
        symbol = "[OK]" if allowed else "[FAIL]"
        print(f"  {symbol} {role:8s} -> {resource}.{action}: {'ALLOWED' if allowed else 'DENIED'}")


def main() -> None:
    print("=" * 50)
    print("  Module 02: Authentication & Authorization")
    print("=" * 50)

    demo_jwt_lifecycle()
    demo_rbac()

    print("\n[DONE] Module 02 demos complete!\n")


if __name__ == "__main__":
    main()
