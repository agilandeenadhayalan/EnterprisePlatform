"""
Exercise 3: A/B Test Router with Statistical Significance
===========================================================

CONCEPT:
When deploying a new ML model, you need to compare it against the current
production model. An A/B test router splits traffic between the two models
and collects outcome metrics to determine which model is better.

Key requirements:
1. DETERMINISTIC routing: the same request_id must always route to the
   same model (for consistent user experience and valid experiments).
2. STATISTICAL significance: you need enough data to be confident that
   one model is truly better, not just lucky.

YOUR TASK:
Implement two methods:
- route_request(): Hash-based deterministic routing.
- compute_significance(): Two-sample t-test to compare model outcomes.

HINTS for route_request():
- Use hashlib.md5(request_id.encode()).hexdigest() to get a hex hash.
- Convert to int, mod by 10000, divide by 10000 to get a float in [0, 1).
- Route to challenger if this float < traffic_split.

HINTS for compute_significance():
- The t-statistic measures the difference between means relative to
  the uncertainty (standard error).
- t = (mean_a - mean_b) / sqrt(var_a/n_a + var_b/n_b)
- A common threshold: |t| > 1.96 for 95% confidence.
"""

import hashlib
import math


class ABTestRouter:
    """Routes requests between champion and challenger models."""

    def __init__(
        self,
        champion: str,
        challenger: str,
        traffic_split: float = 0.1,
    ) -> None:
        """Initialize the router.

        Args:
            champion: Name of the current production model.
            challenger: Name of the model being tested.
            traffic_split: Fraction of traffic for challenger (0.0 to 1.0).
        """
        self.champion = champion
        self.challenger = challenger
        self.traffic_split = traffic_split
        self._outcomes: dict[str, list[float]] = {champion: [], challenger: []}

    def route_request(self, request_id: str) -> str:
        """Route a request to either champion or challenger.

        Must be DETERMINISTIC: same request_id always returns same model.

        Steps:
        1. Hash the request_id using MD5.
        2. Convert to an integer.
        3. Map to a float in [0, 1) using modulo.
        4. Return challenger if float < traffic_split, else champion.

        Args:
            request_id: Unique request identifier.

        Returns:
            The model name ('champion' or 'challenger' name).
        """
        # TODO: Implement (~4 lines)
        raise NotImplementedError("Implement hash-based deterministic routing")

    def record_outcome(self, model: str, value: float) -> None:
        """Record an outcome metric for a model.

        Args:
            model: Which model produced this outcome.
            value: The outcome value (higher = better).
        """
        self._outcomes[model].append(value)

    def compute_significance(self) -> dict:
        """Compute statistical significance of the difference.

        Uses a two-sample t-test (Welch's t-test) which:
        1. Computes the mean and variance of each group.
        2. Computes the t-statistic:
           t = (mean_champion - mean_challenger) / sqrt(var_c/n_c + var_ch/n_ch)
        3. Compares |t| against 1.96 (95% confidence threshold).

        Returns:
            Dict with:
            - champion_mean: mean outcome for champion
            - challenger_mean: mean outcome for challenger
            - t_statistic: the computed t-statistic
            - significant: True if |t| > 1.96 (95% confidence)
            - winner: 'champion', 'challenger', or 'no_winner'

        Returns dict with winner='no_winner' if either group has < 2 samples.
        """
        # TODO: Implement (~20 lines)
        # 1. Get outcomes for each model
        # 2. Check we have enough samples (>= 2 each)
        # 3. Compute means and variances
        #    variance = sum((x - mean)^2) / (n - 1)  [sample variance]
        # 4. Compute standard error = sqrt(var_a/n_a + var_b/n_b)
        # 5. Compute t = (mean_a - mean_b) / standard_error
        # 6. significant = |t| > 1.96
        # 7. winner = model with higher mean (if significant), else 'no_winner'
        raise NotImplementedError("Implement the t-test significance computation")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def _verify():
    """Run basic checks to verify your implementation."""

    # Test deterministic routing
    router = ABTestRouter("model_v1", "model_v2", traffic_split=0.3)

    results = {}
    for i in range(1000):
        model = router.route_request(f"req_{i}")
        results[model] = results.get(model, 0) + 1

    # Should be deterministic -- same call twice gives same result
    for i in range(10):
        assert (
            router.route_request(f"req_{i}")
            == router.route_request(f"req_{i}")
        ), "Routing must be deterministic!"

    # Traffic split should be approximately correct
    challenger_pct = results.get("model_v2", 0) / 1000
    assert 0.15 < challenger_pct < 0.45, (
        f"Challenger got {challenger_pct:.1%}, expected ~30%"
    )
    print(f"[PASS] Deterministic routing: champion={results['model_v1']}, "
          f"challenger={results['model_v2']}")

    # Test significance with clearly different distributions
    router2 = ABTestRouter("old_model", "new_model", traffic_split=0.5)
    import random
    rng = random.Random(42)
    for _ in range(100):
        router2.record_outcome("old_model", rng.gauss(5.0, 1.0))
        router2.record_outcome("new_model", rng.gauss(7.0, 1.0))

    result = router2.compute_significance()
    assert result["significant"], "Should detect significant difference"
    assert result["winner"] == "new_model", "New model should win (higher mean)"
    print(f"[PASS] Significance test: t={result['t_statistic']:.2f}, "
          f"winner={result['winner']}")

    # Test with no significant difference
    router3 = ABTestRouter("a", "b", traffic_split=0.5)
    for _ in range(20):
        router3.record_outcome("a", rng.gauss(5.0, 2.0))
        router3.record_outcome("b", rng.gauss(5.0, 2.0))

    result3 = router3.compute_significance()
    print(f"[INFO] Similar distributions: t={result3['t_statistic']:.2f}, "
          f"significant={result3['significant']}")

    print("[PASS] All verifications passed!")


if __name__ == "__main__":
    _verify()
