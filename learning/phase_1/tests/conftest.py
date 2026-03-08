"""
Phase 1 test fixtures.
"""

import pytest


@pytest.fixture
def sample_users() -> list[dict]:
    """Sample user data for testing."""
    return [
        {"id": "user-001", "name": "Alice", "email": "alice@test.com", "role": "rider"},
        {"id": "user-002", "name": "Bob", "email": "bob@test.com", "role": "driver"},
        {"id": "user-003", "name": "Charlie", "email": "charlie@test.com", "role": "admin"},
    ]


@pytest.fixture
def sample_routes() -> list[dict]:
    """Sample API gateway routes for testing."""
    return [
        {"pattern": "/api/v1/users", "service": "user-service", "methods": ["GET", "POST"]},
        {"pattern": "/api/v1/auth", "service": "auth-service", "methods": ["POST"]},
        {"pattern": "/api/v1/trips", "service": "trip-service", "methods": ["GET", "POST"]},
    ]
