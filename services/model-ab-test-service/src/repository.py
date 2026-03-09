"""
Model A/B test repository — in-memory test store.

Pre-seeds with 2 A/B tests: 1 active with 100+ recorded outcomes per variant,
1 concluded with a winner. Routing uses hash of request_id modulo 100 vs
traffic_split * 100.
"""

import math
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import ABTest, SignificanceResult


class ABTestRepository:
    """In-memory A/B test store."""

    def __init__(self, seed: bool = True):
        self._tests: dict[str, ABTest] = {}
        self._rng = random.Random(42)
        if seed:
            self._seed()

    def _seed(self):
        """Pre-seed with 2 A/B tests."""
        # Active test with 100+ outcomes per variant
        test1 = ABTest(
            id="ab-001",
            name="Fare Model v2.1 vs v2.0",
            champion_model="fare_predictor_v2.0",
            challenger_model="fare_predictor_v2.1",
            traffic_split=0.3,
            status="active",
            created_at="2024-01-15T08:00:00+00:00",
        )
        # Seed champion outcomes (70% traffic)
        rng = self._rng
        for _ in range(150):
            test1.champion.record_outcome(round(rng.gauss(25.0, 5.0), 2))
        # Seed challenger outcomes (30% traffic)
        for _ in range(120):
            test1.challenger.record_outcome(round(rng.gauss(26.5, 4.8), 2))
        self._tests[test1.id] = test1

        # Concluded test with winner
        test2 = ABTest(
            id="ab-002",
            name="ETA Model v3.0 vs v2.5",
            champion_model="eta_predictor_v2.5",
            challenger_model="eta_predictor_v3.0",
            traffic_split=0.5,
            status="concluded",
            winner="challenger",
            created_at="2024-01-01T08:00:00+00:00",
            concluded_at="2024-01-14T18:00:00+00:00",
        )
        for _ in range(200):
            test2.champion.record_outcome(round(rng.gauss(8.5, 2.0), 2))
        for _ in range(200):
            test2.challenger.record_outcome(round(rng.gauss(7.2, 1.8), 2))
        self._tests[test2.id] = test2

    def create_test(
        self,
        name: str,
        champion_model: str,
        challenger_model: str,
        traffic_split: float = 0.5,
    ) -> ABTest:
        """Create a new A/B test."""
        test_id = f"ab-{uuid.uuid4().hex[:8]}"
        test = ABTest(
            id=test_id,
            name=name,
            champion_model=champion_model,
            challenger_model=challenger_model,
            traffic_split=traffic_split,
        )
        self._tests[test_id] = test
        return test

    def list_tests(self, status: Optional[str] = None) -> list[ABTest]:
        """List A/B tests, optionally filtered by status."""
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        return sorted(tests, key=lambda t: t.created_at, reverse=True)

    def get_test(self, test_id: str) -> Optional[ABTest]:
        """Get an A/B test by ID."""
        return self._tests.get(test_id)

    def route_request(self, test_id: str, request_id: str) -> Optional[dict]:
        """Route a request to champion or challenger based on hash."""
        test = self._tests.get(test_id)
        if test is None or test.status != "active":
            return None

        # Deterministic routing: hash(request_id) % 100 < traffic_split * 100 => challenger
        hash_val = hash(request_id) % 100
        threshold = int(test.traffic_split * 100)

        if hash_val < threshold:
            variant = "challenger"
            model_name = test.challenger_model
        else:
            variant = "champion"
            model_name = test.champion_model

        return {
            "variant": variant,
            "model_name": model_name,
            "test_id": test_id,
        }

    def record_outcome(
        self, test_id: str, variant: str, value: float
    ) -> Optional[ABTest]:
        """Record an outcome for a variant."""
        test = self._tests.get(test_id)
        if test is None:
            return None
        if variant == "champion":
            test.champion.record_outcome(value)
        elif variant == "challenger":
            test.challenger.record_outcome(value)
        return test

    def conclude_test(self, test_id: str) -> Optional[ABTest]:
        """Conclude an A/B test and declare a winner."""
        test = self._tests.get(test_id)
        if test is None or test.status != "active":
            return None

        # Determine winner based on higher average value
        if test.challenger.avg_value > test.champion.avg_value:
            test.winner = "challenger"
        else:
            test.winner = "champion"

        test.status = "concluded"
        test.concluded_at = datetime.now(timezone.utc).isoformat()
        return test

    def check_significance(self, test_id: str) -> Optional[SignificanceResult]:
        """Check statistical significance using Welch's t-test approximation."""
        test = self._tests.get(test_id)
        if test is None:
            return None

        n_a = test.champion.request_count
        n_b = test.challenger.request_count

        if n_a < 2 or n_b < 2:
            return SignificanceResult(
                p_value=1.0,
                is_significant=False,
                recommended_action="Collect more data (minimum 2 samples per variant)",
            )

        vals_a = test.champion.values
        vals_b = test.challenger.values

        mean_a = sum(vals_a) / n_a
        mean_b = sum(vals_b) / n_b

        var_a = sum((x - mean_a) ** 2 for x in vals_a) / (n_a - 1)
        var_b = sum((x - mean_b) ** 2 for x in vals_b) / (n_b - 1)

        se = math.sqrt(var_a / n_a + var_b / n_b) if (var_a / n_a + var_b / n_b) > 0 else 0.001
        t_stat = abs(mean_a - mean_b) / se

        # Approximate p-value using normal distribution for large samples
        # For large n, t-distribution ~ normal
        z = t_stat
        # Simple approximation: p = 2 * (1 - Phi(|z|))
        # Using a basic approximation of the normal CDF
        p_value = 2.0 * (1.0 - _normal_cdf(z))
        p_value = round(max(p_value, 0.0001), 4)

        is_significant = p_value < 0.05

        if not is_significant:
            action = "Continue test — not yet statistically significant"
        elif mean_b > mean_a:
            action = "Promote challenger — statistically significant improvement"
        else:
            action = "Keep champion — challenger did not outperform"

        return SignificanceResult(
            p_value=p_value,
            is_significant=is_significant,
            recommended_action=action,
        )


def _normal_cdf(x: float) -> float:
    """Approximate the standard normal CDF using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


repo = ABTestRepository(seed=True)
