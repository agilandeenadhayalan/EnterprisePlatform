"""
Tests for feature flag service — flag evaluation logic, schema validation, and rollout hashing.

These tests verify:
1. Flag evaluation decision tree (the most important tests!)
   - Flag disabled globally -> False
   - Flag enabled, no restrictions -> True
   - Flag enabled, role restriction, matching role -> True
   - Flag enabled, role restriction, non-matching role -> False
   - Flag enabled, rollout percentage -> deterministic hash
   - User override wins regardless of flag state
2. Schema validation for create/update requests
3. Rollout percentage hash consistency

No database needed — these are pure unit tests. The evaluate logic is
tested by importing the hash function and replicating the decision tree.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add paths for flat imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import hashlib
import pytest

from repository import compute_rollout_hash


# ── Helper: replicate the evaluation decision tree for unit testing ──

def evaluate_flag_logic(
    is_enabled: bool,
    rollout_percentage: int,
    target_roles: list[str] | None,
    user_id: str,
    user_role: str,
    override: bool | None = None,
) -> tuple[bool, str]:
    """
    Pure-function version of the flag evaluation decision tree.

    This mirrors repository.FeatureFlagRepository.evaluate_flag but without
    any database access, so we can test the logic in isolation.
    """
    # Step 1: Check user-specific override
    if override is not None:
        status = "enabled" if override else "disabled"
        return override, f"user override: {status}"

    # Step 2: Check global enabled state
    if not is_enabled:
        return False, "flag is globally disabled"

    # Step 3: Check target roles
    if target_roles and len(target_roles) > 0:
        if user_role not in target_roles:
            return False, f"user role '{user_role}' not in target roles"

    # Step 4: Check rollout percentage
    if rollout_percentage < 100:
        hash_value = compute_rollout_hash(user_id, "test-flag")
        if hash_value < rollout_percentage:
            return True, f"user included in {rollout_percentage}% rollout (hash={hash_value})"
        else:
            return False, f"user excluded from {rollout_percentage}% rollout (hash={hash_value})"

    # Step 5: Flag enabled, no restrictions
    return True, "flag enabled, no restrictions"


class TestFlagEvaluationLogic:
    """
    Test the flag evaluation decision tree — the core business logic.

    This is the most important test class. It covers every branch of the
    decision tree without needing a database.
    """

    def test_flag_disabled_globally(self):
        """A globally disabled flag should evaluate to False."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=False,
            rollout_percentage=100,
            target_roles=None,
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is False
        assert "globally disabled" in reason

    def test_flag_enabled_no_restrictions(self):
        """An enabled flag with no role/rollout restrictions should be True."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,
            rollout_percentage=100,
            target_roles=None,
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is True
        assert "no restrictions" in reason

    def test_flag_enabled_matching_role(self):
        """Flag enabled, target_roles=['admin', 'rider'], user is rider -> True."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,
            rollout_percentage=100,
            target_roles=["admin", "rider"],
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is True
        assert "no restrictions" in reason

    def test_flag_enabled_non_matching_role(self):
        """Flag enabled, target_roles=['admin'], user is rider -> False."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,
            rollout_percentage=100,
            target_roles=["admin"],
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is False
        assert "not in target roles" in reason
        assert "rider" in reason

    def test_flag_enabled_rollout_included(self):
        """
        Flag with rollout percentage — find a user_id that falls within the rollout.

        We use the actual hash function to find a user_id that produces
        a hash value below the rollout percentage.
        """
        # Find a user_id that hashes below 50
        for i in range(1000):
            test_id = f"user-{i}"
            hash_val = compute_rollout_hash(test_id, "test-flag")
            if hash_val < 50:
                enabled, reason = evaluate_flag_logic(
                    is_enabled=True,
                    rollout_percentage=50,
                    target_roles=None,
                    user_id=test_id,
                    user_role="rider",
                )
                assert enabled is True
                assert "included" in reason
                assert "50%" in reason
                return

        pytest.fail("Could not find a user_id that hashes below 50 in 1000 attempts")

    def test_flag_enabled_rollout_excluded(self):
        """
        Flag with rollout percentage — find a user_id excluded from rollout.
        """
        # Find a user_id that hashes at or above 50
        for i in range(1000):
            test_id = f"user-{i}"
            hash_val = compute_rollout_hash(test_id, "test-flag")
            if hash_val >= 50:
                enabled, reason = evaluate_flag_logic(
                    is_enabled=True,
                    rollout_percentage=50,
                    target_roles=None,
                    user_id=test_id,
                    user_role="rider",
                )
                assert enabled is False
                assert "excluded" in reason
                assert "50%" in reason
                return

        pytest.fail("Could not find a user_id that hashes at/above 50 in 1000 attempts")

    def test_override_enabled_wins_over_disabled_flag(self):
        """User override=True should win even if flag is globally disabled."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=False,  # flag disabled
            rollout_percentage=100,
            target_roles=None,
            user_id="user-123",
            user_role="rider",
            override=True,  # but user has override
        )
        assert enabled is True
        assert "user override" in reason
        assert "enabled" in reason

    def test_override_disabled_wins_over_enabled_flag(self):
        """User override=False should win even if flag is globally enabled."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,  # flag enabled
            rollout_percentage=100,
            target_roles=None,
            user_id="user-123",
            user_role="admin",
            override=False,  # but user has override disabling it
        )
        assert enabled is False
        assert "user override" in reason
        assert "disabled" in reason

    def test_empty_target_roles_allows_all(self):
        """Empty target_roles list (no roles set) should allow all users."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,
            rollout_percentage=100,
            target_roles=[],
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is True
        assert "no restrictions" in reason

    def test_zero_percent_rollout_blocks_everyone(self):
        """0% rollout should block all users (no hash can be < 0)."""
        enabled, reason = evaluate_flag_logic(
            is_enabled=True,
            rollout_percentage=0,
            target_roles=None,
            user_id="user-123",
            user_role="rider",
        )
        assert enabled is False
        assert "excluded" in reason


class TestRolloutHash:
    """Test the rollout hash function for consistency and distribution."""

    def test_hash_deterministic(self):
        """Same user_id + flag_name should always produce the same hash."""
        h1 = compute_rollout_hash("user-abc", "dark-mode")
        h2 = compute_rollout_hash("user-abc", "dark-mode")
        assert h1 == h2

    def test_hash_range(self):
        """Hash should always be in range [0, 99]."""
        for i in range(500):
            h = compute_rollout_hash(f"user-{i}", "test-flag")
            assert 0 <= h <= 99

    def test_hash_varies_by_user(self):
        """Different users should (mostly) get different hashes."""
        hashes = {compute_rollout_hash(f"user-{i}", "test-flag") for i in range(100)}
        # With 100 users and 100 buckets, we'd expect at least 50 unique values
        assert len(hashes) > 50

    def test_hash_varies_by_flag(self):
        """Same user with different flags should get different hashes."""
        h1 = compute_rollout_hash("user-123", "flag-a")
        h2 = compute_rollout_hash("user-123", "flag-b")
        # These could theoretically collide, but it's extremely unlikely
        assert h1 != h2

    def test_hash_consistency_known_value(self):
        """
        Verify the hash function produces a known value.

        This ensures the implementation doesn't accidentally change.
        """
        h = compute_rollout_hash("test-user-id", "test-flag-name")
        # Re-compute manually to get the expected value
        combined = "test-user-id:test-flag-name"
        expected = int.from_bytes(
            hashlib.sha256(combined.encode()).digest()[:4], byteorder="big"
        ) % 100
        assert h == expected

    def test_rollout_50_percent_rough_distribution(self):
        """
        50% rollout should include roughly half of users.

        With 10000 users, we expect ~5000 to be included. Allow 10% tolerance.
        """
        included = 0
        total = 10000
        for i in range(total):
            h = compute_rollout_hash(f"user-{i}", "50-pct-flag")
            if h < 50:
                included += 1

        ratio = included / total
        assert 0.40 < ratio < 0.60, f"Expected ~50%, got {ratio * 100:.1f}%"


class TestFlagSchemas:
    """Test Pydantic schema validation for feature flag requests/responses."""

    def test_create_flag_request_minimal(self):
        """CreateFlagRequest with just flag_name should use defaults."""
        from schemas import CreateFlagRequest

        req = CreateFlagRequest(flag_name="dark-mode")
        assert req.flag_name == "dark-mode"
        assert req.is_enabled is False
        assert req.rollout_percentage == 100
        assert req.target_roles is None

    def test_create_flag_request_full(self):
        """CreateFlagRequest with all fields should validate."""
        from schemas import CreateFlagRequest

        req = CreateFlagRequest(
            flag_name="new-dashboard",
            description="New dashboard UI for beta testers",
            is_enabled=True,
            rollout_percentage=25,
            target_roles=["admin", "beta_tester"],
            metadata={"jira_ticket": "MOB-1234"},
        )
        assert req.flag_name == "new-dashboard"
        assert req.is_enabled is True
        assert req.rollout_percentage == 25
        assert req.target_roles == ["admin", "beta_tester"]

    def test_create_flag_request_invalid_percentage(self):
        """Rollout percentage must be 0-100."""
        from schemas import CreateFlagRequest

        with pytest.raises(Exception):
            CreateFlagRequest(flag_name="test", rollout_percentage=101)

        with pytest.raises(Exception):
            CreateFlagRequest(flag_name="test", rollout_percentage=-1)

    def test_update_flag_request_partial(self):
        """UpdateFlagRequest should allow partial updates (all fields optional)."""
        from schemas import UpdateFlagRequest

        req = UpdateFlagRequest(is_enabled=True)
        assert req.is_enabled is True
        assert req.description is None
        assert req.rollout_percentage is None

    def test_evaluate_flag_response(self):
        """EvaluateFlagResponse should include flag_name, is_enabled, reason."""
        from schemas import EvaluateFlagResponse

        resp = EvaluateFlagResponse(
            flag_name="dark-mode",
            is_enabled=True,
            reason="flag enabled, no restrictions",
        )
        assert resp.flag_name == "dark-mode"
        assert resp.is_enabled is True
        assert "no restrictions" in resp.reason

    def test_override_request(self):
        """OverrideRequest should require user_id and is_enabled."""
        from schemas import OverrideRequest

        req = OverrideRequest(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            is_enabled=True,
            reason="Beta tester opt-in",
        )
        assert req.user_id == "550e8400-e29b-41d4-a716-446655440000"
        assert req.is_enabled is True
        assert req.reason == "Beta tester opt-in"

    def test_flag_response_schema(self):
        """FlagResponse should accept all required fields."""
        from schemas import FlagResponse

        now = datetime.now(timezone.utc)
        flag = FlagResponse(
            id="123",
            flag_name="dark-mode",
            description="Enable dark mode UI",
            is_enabled=True,
            rollout_percentage=50,
            target_roles=["admin"],
            metadata={"owner": "frontend-team"},
            created_at=now,
            updated_at=now,
        )
        assert flag.flag_name == "dark-mode"
        assert flag.rollout_percentage == 50

    def test_flag_list_response(self):
        """FlagListResponse wraps flags with a count."""
        from schemas import FlagResponse, FlagListResponse

        now = datetime.now(timezone.utc)
        flags = [
            FlagResponse(
                id=f"id-{i}",
                flag_name=f"flag-{i}",
                is_enabled=True,
                rollout_percentage=100,
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]
        response = FlagListResponse(flags=flags, count=3)
        assert response.count == 3
        assert len(response.flags) == 3


class TestFeatureFlagConfig:
    """Verify feature flag service configuration defaults."""

    def test_config_defaults(self):
        """Config should load with correct service name and port."""
        from config import settings

        assert settings.service_name == "feature-flag-service"
        assert settings.service_port == 8031

    def test_database_url_format(self):
        """database_url property should produce a valid asyncpg URL."""
        from config import settings

        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.postgres_db in settings.database_url

    def test_redis_url_format(self):
        """redis_url property should produce a valid Redis URL."""
        from config import settings

        assert settings.redis_url.startswith("redis://")


class TestSecurityImports:
    """Verify that mobility-common security middleware is importable."""

    def test_require_role_import(self):
        """The require_role dependency factory should be importable."""
        from mobility_common.fastapi.middleware import require_role
        assert callable(require_role)

    def test_get_current_user_import(self):
        """The get_current_user dependency should be importable."""
        from mobility_common.fastapi.middleware import get_current_user
        assert callable(get_current_user)

    def test_error_helpers_import(self):
        """Error factory functions should be importable."""
        from mobility_common.fastapi.errors import not_found, conflict
        assert callable(not_found)
        assert callable(conflict)
