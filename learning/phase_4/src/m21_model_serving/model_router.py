"""
Model Routing Strategies
=========================

When deploying ML models in production, you rarely just swap one model
for another. Instead, you use routing strategies to gradually and safely
introduce new models:

**A/B Test Router**: Splits traffic between a champion (current best) and
  a challenger (new model). Uses deterministic hashing so the same user
  always sees the same model -- essential for consistent experiences and
  valid statistical comparisons.

**Shadow Router**: Sends all requests to BOTH models but only returns the
  primary model's result. The shadow model's predictions are logged for
  offline comparison. This is zero-risk because users never see shadow
  results.

**Canary Router**: Starts with a tiny fraction of traffic (e.g., 1%) on
  the new model and gradually increases. If metrics degrade, roll back
  immediately. This limits blast radius.

These patterns can be combined:
1. First shadow-test to verify the new model doesn't crash.
2. Then canary at 1% to check real-world metrics.
3. Then A/B test at 50/50 for statistical significance.
4. Finally, promote the winner to 100%.
"""

from __future__ import annotations

import hashlib


class ABTestRouter:
    """Routes requests between champion and challenger models.

    Uses deterministic hashing of request_id to ensure:
    - The same request always routes to the same model.
    - Traffic split is approximately correct over many requests.
    - No randomness -- fully reproducible.

    Also tracks outcomes for each model to compare performance.
    """

    def __init__(
        self,
        champion: str,
        challenger: str,
        traffic_split: float = 0.1,
    ) -> None:
        """Initialize the A/B test router.

        Args:
            champion: Name of the current production model.
            challenger: Name of the model being tested.
            traffic_split: Fraction of traffic to send to challenger (0.0-1.0).
        """
        if not 0.0 <= traffic_split <= 1.0:
            raise ValueError("traffic_split must be between 0.0 and 1.0")
        self.champion = champion
        self.challenger = challenger
        self.traffic_split = traffic_split
        self._outcomes: dict[str, list[dict]] = {champion: [], challenger: []}
        self._routing_log: dict[str, str] = {}

    def route(self, request_id: str) -> str:
        """Route a request to either champion or challenger.

        Uses MD5 hash of request_id mapped to [0, 1) to determine routing.
        This is deterministic: same request_id always gets the same model.

        Args:
            request_id: Unique request identifier.

        Returns:
            The model name to handle this request.
        """
        # Hash to a float in [0, 1)
        hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        fraction = (hash_value % 10000) / 10000.0

        model = self.challenger if fraction < self.traffic_split else self.champion
        self._routing_log[request_id] = model
        return model

    def record_outcome(self, request_id: str, model: str, value: float) -> None:
        """Record the outcome of a request for later analysis.

        Args:
            request_id: The request identifier.
            model: Which model handled it.
            value: The outcome metric (e.g., prediction accuracy, revenue).
        """
        if model not in self._outcomes:
            self._outcomes[model] = []
        self._outcomes[model].append({
            "request_id": request_id,
            "value": value,
        })

    def get_metrics(self) -> dict:
        """Compare champion and challenger performance.

        Returns:
            Dict with per-model count, mean, and all outcomes.
        """
        metrics = {}
        for model, outcomes in self._outcomes.items():
            values = [o["value"] for o in outcomes]
            metrics[model] = {
                "count": len(values),
                "mean": sum(values) / len(values) if values else 0.0,
                "outcomes": values,
            }
        return metrics


class ShadowRouter:
    """Routes to both models but only returns primary result.

    Shadow testing lets you evaluate a new model in production without
    any risk to users. Both models process every request, but only the
    primary model's result is returned. The shadow model's predictions
    are logged for offline comparison.

    Use this when you want to:
    - Verify the new model doesn't crash on production inputs.
    - Compare prediction distributions.
    - Measure latency differences.
    """

    def __init__(self, primary: str, shadow: str) -> None:
        self.primary = primary
        self.shadow = shadow
        self._log: list[dict] = []

    def route(self, request_id: str) -> tuple[str, str]:
        """Route a request to both primary and shadow models.

        Args:
            request_id: Unique request identifier.

        Returns:
            Tuple of (primary_model, shadow_model) names.
            Both should be called, but only primary's result is returned
            to the user.
        """
        self._log.append({"request_id": request_id})
        return (self.primary, self.shadow)

    def record_comparison(
        self,
        request_id: str,
        primary_result: float,
        shadow_result: float,
    ) -> None:
        """Record prediction comparison for offline analysis."""
        self._log.append({
            "request_id": request_id,
            "primary_result": primary_result,
            "shadow_result": shadow_result,
            "diff": abs(primary_result - shadow_result),
        })

    def get_divergence_stats(self) -> dict:
        """Compute how much the shadow diverges from primary.

        Returns:
            Dict with count, mean_diff, max_diff of prediction differences.
        """
        comparisons = [e for e in self._log if "diff" in e]
        if not comparisons:
            return {"count": 0, "mean_diff": 0.0, "max_diff": 0.0}

        diffs = [c["diff"] for c in comparisons]
        return {
            "count": len(diffs),
            "mean_diff": sum(diffs) / len(diffs),
            "max_diff": max(diffs),
        }


class CanaryRouter:
    """Gradual rollout -- slowly increases traffic to new model.

    Unlike A/B testing (fixed split), canary deployment starts with a
    tiny percentage and gradually increases:
    1% -> 5% -> 10% -> 25% -> 50% -> 100%

    At each step, monitor metrics. If anything goes wrong, rollback()
    immediately sends all traffic back to the stable model.

    This limits the "blast radius" of a bad model to a small number
    of users.
    """

    def __init__(
        self,
        stable: str,
        canary: str,
        initial_pct: float = 1.0,
        max_pct: float = 100.0,
        step_pct: float = 5.0,
    ) -> None:
        """Initialize the canary router.

        Args:
            stable: Name of the current stable model.
            canary: Name of the new model being rolled out.
            initial_pct: Starting percentage for the canary (0-100).
            max_pct: Maximum percentage for the canary (0-100).
            step_pct: How much to increase on each promote() call.
        """
        if not 0.0 <= initial_pct <= 100.0:
            raise ValueError("initial_pct must be between 0 and 100")
        if not 0.0 <= max_pct <= 100.0:
            raise ValueError("max_pct must be between 0 and 100")

        self.stable = stable
        self.canary = canary
        self.current_pct = initial_pct
        self.max_pct = max_pct
        self.step_pct = step_pct
        self._promotion_history: list[float] = [initial_pct]

    def route(self, request_id: str) -> str:
        """Route a request based on current canary percentage.

        Uses deterministic hashing like ABTestRouter.
        """
        hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        fraction = (hash_value % 10000) / 100.0  # 0-100 range

        return self.canary if fraction < self.current_pct else self.stable

    def promote(self) -> float:
        """Increase canary traffic by step_pct.

        Returns:
            The new canary percentage.
        """
        self.current_pct = min(self.current_pct + self.step_pct, self.max_pct)
        self._promotion_history.append(self.current_pct)
        return self.current_pct

    def rollback(self) -> float:
        """Immediately set canary traffic to 0%.

        Returns:
            The new canary percentage (0.0).
        """
        self.current_pct = 0.0
        self._promotion_history.append(0.0)
        return self.current_pct

    @property
    def promotion_history(self) -> list[float]:
        """Return the history of canary percentage changes."""
        return list(self._promotion_history)

    @property
    def is_fully_rolled_out(self) -> bool:
        """Check if canary has reached max_pct."""
        return self.current_pct >= self.max_pct
