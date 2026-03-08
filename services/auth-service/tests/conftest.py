"""
Test fixtures for auth service.

Uses FastAPI's TestClient with dependency overrides to test routes
without a real PostgreSQL database. The get_db dependency is replaced
with an in-memory SQLite session.
"""

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock

import security


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "rider@test.com",
        "password": "SecurePass123!",
        "full_name": "Test Rider",
        "phone": "+1234567890",
    }


@pytest.fixture
def sample_password_hash():
    """Pre-computed bcrypt hash for 'SecurePass123!'."""
    return security.hash_password("SecurePass123!")
