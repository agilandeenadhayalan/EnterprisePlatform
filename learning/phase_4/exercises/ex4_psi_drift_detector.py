"""
Exercise 4: PSI Drift Detector
========================================
Population Stability Index measures how much a feature's distribution
has shifted from training to production.

PSI = sum( (actual% - expected%) * ln(actual% / expected%) )

    PSI < 0.1  = stable (no significant drift)
    0.1 - 0.25 = moderate drift (investigate)
    > 0.25     = significant drift (model likely degraded)

WHY PSI:
In production ML, your model was trained on historical data. Over time,
the input distribution shifts (new user demographics, seasonal changes,
market shifts). PSI gives a single number that quantifies HOW MUCH the
distribution has moved, enabling automated monitoring and alerts.

YOUR TASK:
1. Implement _compute_psi_bucket() — PSI formula for one histogram bin
2. Implement compute_psi() — bin the data and sum PSI across bins
"""

import math


class PSIDriftDetector:
    """Detect distribution drift using Population Stability Index."""

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins

    def _compute_psi_bucket(self, expected_pct: float, actual_pct: float) -> float:
        """Compute PSI for a single bucket.

        Formula: (actual% - expected%) * ln(actual% / expected%)

        Handle edge cases where percentages are 0 by adding a small
        epsilon (1e-6) to avoid log(0) and division by zero.

        Args:
            expected_pct: Proportion of reference data in this bin.
            actual_pct: Proportion of current data in this bin.

        Returns:
            PSI contribution from this single bin.
        """
        # TODO: Implement (~3 lines)
        # Hint: Add epsilon to both percentages before computing
        raise NotImplementedError("Implement PSI bucket formula")

    def compute_psi(self, reference: list[float], current: list[float]) -> float:
        """Compute total PSI between reference and current distributions.

        Steps:
        1. Determine bin edges from reference data (evenly spaced between
           min and max of reference)
        2. Count what fraction of reference falls in each bin (expected%)
        3. Count what fraction of current falls in each bin (actual%)
        4. Sum _compute_psi_bucket() across all bins

        Args:
            reference: The training/reference distribution.
            current: The production/current distribution.

        Returns:
            Total PSI score.
        """
        # TODO: Implement (~8 lines)
        # Hint: Use min/max of reference for bin edges
        # Hint: For each bin, count values in [edge_i, edge_{i+1})
        # Hint: Last bin should include the max value (use <=)
        raise NotImplementedError("Implement full PSI computation")

    def classify(self, psi: float) -> str:
        """Classify drift severity based on PSI value.
        PROVIDED — do not modify.
        """
        if psi < 0.1:
            return "no_drift"
        elif psi < 0.25:
            return "moderate"
        return "significant"


# ── Verification ──

def _verify():
    """Run basic checks to verify your implementation."""
    det = PSIDriftDetector()

    # Test 1: Identical distributions should have PSI near 0
    data = [1.0, 2.0, 3.0, 4.0, 5.0] * 20
    psi = det.compute_psi(data, data)
    assert psi < 0.01, f"Expected PSI < 0.01 for identical data, got {psi:.4f}"
    print(f"[PASS] Identical distributions: PSI = {psi:.4f}")

    # Test 2: Shifted distribution should have high PSI
    import random
    rng = random.Random(42)
    ref = [rng.gauss(0, 1) for _ in range(200)]
    cur = [rng.gauss(2, 1) for _ in range(200)]
    psi = det.compute_psi(ref, cur)
    assert psi > 0.25, f"Expected PSI > 0.25 for shifted data, got {psi:.4f}"
    print(f"[PASS] Shifted distributions: PSI = {psi:.4f}")

    # Test 3: Classification
    assert det.classify(0.05) == "no_drift"
    assert det.classify(0.15) == "moderate"
    assert det.classify(0.30) == "significant"
    print("[PASS] Classification correct")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
