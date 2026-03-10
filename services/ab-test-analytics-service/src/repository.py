"""
In-memory AB test analytics repository with pre-seeded data.
"""

import math
import uuid
from datetime import datetime, timezone

from models import ABTestResult, SequentialTestResult


class ABTestAnalyticsRepository:
    """In-memory store for AB test results and sequential tests."""

    def __init__(self, seed: bool = False):
        self.results: list[ABTestResult] = []
        self.sequential_results: list[SequentialTestResult] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        results = [
            ABTestResult("abt-001", "exp-001", "conversion_rate", 1000, 120, 1000, 155, 2.45, 0.014, True, now),
            ABTestResult("abt-002", "exp-001", "revenue_per_user", 1000, 200, 1000, 230, 1.96, 0.05, True, now),
            ABTestResult("abt-003", "exp-002", "click_through_rate", 500, 50, 500, 75, 2.89, 0.004, True, now),
            ABTestResult("abt-004", "exp-003", "signup_rate", 800, 80, 800, 85, 0.52, 0.603, False, now),
            ABTestResult("abt-005", "exp-004", "bounce_rate", 600, 180, 600, 175, -0.29, 0.772, False, now),
        ]
        self.results.extend(results)

        seq_results = [
            SequentialTestResult("seq-001", "exp-001", 500, 2.85, 2.80, True, now),
            SequentialTestResult("seq-002", "exp-002", 300, 1.20, 2.96, False, now),
            SequentialTestResult("seq-003", "exp-003", 700, 1.50, 2.88, False, now),
        ]
        self.sequential_results.extend(seq_results)

    # ── Z-test helpers ──

    @staticmethod
    def _z_score(control_count: int, control_conversions: int,
                 variant_count: int, variant_conversions: int) -> float:
        p1 = control_conversions / control_count if control_count > 0 else 0
        p2 = variant_conversions / variant_count if variant_count > 0 else 0
        p_pool = (control_conversions + variant_conversions) / (control_count + variant_count)
        if p_pool == 0 or p_pool == 1:
            return 0.0
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / control_count + 1 / variant_count))
        if se == 0:
            return 0.0
        return (p2 - p1) / se

    @staticmethod
    def _p_value(z: float) -> float:
        """Approximate two-tailed p-value from z-score using normal CDF approximation."""
        # Abramowitz and Stegun approximation
        az = abs(z)
        if az > 6:
            return 0.0
        t = 1.0 / (1.0 + 0.2316419 * az)
        d = 0.3989422802 * math.exp(-az * az / 2.0)
        p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
        return 2.0 * p  # two-tailed

    # ── Run test ──

    def run_test(self, data: dict) -> ABTestResult:
        z = self._z_score(
            data["control_count"], data["control_conversions"],
            data["variant_count"], data["variant_conversions"],
        )
        p = self._p_value(z)
        significant = p < 0.05
        now = datetime.now(timezone.utc).isoformat()
        result = ABTestResult(
            id=f"abt-{uuid.uuid4().hex[:8]}",
            experiment_id=data["experiment_id"],
            metric=data["metric"],
            control_count=data["control_count"],
            control_conversions=data["control_conversions"],
            variant_count=data["variant_count"],
            variant_conversions=data["variant_conversions"],
            z_score=round(z, 4),
            p_value=round(p, 4),
            significant=significant,
            created_at=now,
        )
        self.results.append(result)
        return result

    # ── Results ──

    def list_results(self, experiment_id: str | None = None) -> list[ABTestResult]:
        if experiment_id:
            return [r for r in self.results if r.experiment_id == experiment_id]
        return list(self.results)

    def get_result(self, result_id: str) -> ABTestResult | None:
        for r in self.results:
            if r.id == result_id:
                return r
        return None

    # ── Power calculation ──

    @staticmethod
    def calc_power(alpha: float, power: float, mde: float) -> dict:
        """Calculate sample size needed per group."""
        # z_alpha for two-tailed
        z_alpha = ABTestAnalyticsRepository._z_from_alpha(alpha)
        z_beta = ABTestAnalyticsRepository._z_from_alpha((1 - power) * 2)
        if mde == 0:
            return {
                "sample_size_needed": 0,
                "power": power,
                "alpha": alpha,
                "minimum_detectable_effect": mde,
            }
        n = math.ceil(2 * ((z_alpha + z_beta) / mde) ** 2)
        return {
            "sample_size_needed": n,
            "power": power,
            "alpha": alpha,
            "minimum_detectable_effect": mde,
        }

    @staticmethod
    def _z_from_alpha(alpha: float) -> float:
        """Approximate z-value for a given alpha (two-tailed)."""
        # Common z-values
        z_table = {0.01: 2.576, 0.05: 1.96, 0.10: 1.645, 0.20: 1.282, 0.40: 0.842, 0.50: 0.674}
        if alpha in z_table:
            return z_table[alpha]
        # Rational approximation (Abramowitz & Stegun)
        p = alpha / 2.0
        if p <= 0:
            return 3.5
        if p >= 0.5:
            return 0.0
        t = math.sqrt(-2.0 * math.log(p))
        z = t - (2.515517 + t * (0.802853 + t * 0.010328)) / (1.0 + t * (1.432788 + t * (0.189269 + t * 0.001308)))
        return z

    # ── Sequential testing ──

    def run_sequential_test(self, data: dict) -> SequentialTestResult:
        observations = data["observations"]
        successes = data["successes"]
        alpha = data.get("alpha", 0.05)

        # Compute current z-score (proportion test vs 0.5)
        p_hat = successes / observations if observations > 0 else 0
        se = math.sqrt(0.25 / observations) if observations > 0 else 1
        current_z = (p_hat - 0.5) / se if se > 0 else 0

        # O'Brien-Fleming boundary approximation
        z_alpha = self._z_from_alpha(alpha)
        # Simplified: boundary decreases with more observations
        info_fraction = min(observations / 1000.0, 1.0)
        if info_fraction > 0:
            boundary = z_alpha / math.sqrt(info_fraction)
        else:
            boundary = z_alpha * 10

        stopped_early = abs(current_z) > boundary

        now = datetime.now(timezone.utc).isoformat()
        result = SequentialTestResult(
            id=f"seq-{uuid.uuid4().hex[:8]}",
            experiment_id=data["experiment_id"],
            observations=observations,
            current_z=round(current_z, 4),
            boundary=round(boundary, 4),
            stopped_early=stopped_early,
            created_at=now,
        )
        self.sequential_results.append(result)
        return result

    def list_sequential_results(self) -> list[SequentialTestResult]:
        return list(self.sequential_results)

    # ── Stats ──

    def get_stats(self) -> dict:
        total = len(self.results)
        sig_count = sum(1 for r in self.results if r.significant)
        avg_z = sum(abs(r.z_score) for r in self.results) / total if total > 0 else 0.0
        return {
            "total_tests": total,
            "significant_count": sig_count,
            "avg_z_score": round(avg_z, 4),
        }


REPO_CLASS = ABTestAnalyticsRepository
repo = ABTestAnalyticsRepository(seed=True)
