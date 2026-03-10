"""
Exercise 3: Weighted Ensemble Fraud Scoring
========================================
Implement an ensemble scoring function that combines multiple fraud
detectors with different weights and normalizes their outputs.

WHY THIS MATTERS:
No single fraud detector catches all types of fraud. Z-scores catch
statistical outliers, isolation forests catch multivariate anomalies,
and rule-based systems catch known patterns. Combining them with
appropriate weights produces a more robust fraud detection system.

The challenge is that different detectors produce scores on different
scales:
  - Z-score: 0 to infinity (unbounded)
  - Isolation forest: 0 to 1
  - Rule-based: 0 to 1

To combine them, you must first normalize all scores to [0, 1] using
min-max normalization relative to known thresholds, then compute the
weighted average.

YOUR TASK:
Implement ensemble_score(detectors, weights, transaction) that:
1. Gets a raw score from each detector
2. Normalizes each score to [0, 1] using the detector's threshold
   (score / threshold capped at 1.0)
3. Computes the weighted average of normalized scores
"""


class SimpleDetector:
    """A simple detector for testing the ensemble.

    This is provided for you — do not modify.
    """

    def __init__(self, name: str, threshold: float):
        self.name = name
        self.threshold = threshold
        self._score_fn = None

    def set_score_fn(self, fn):
        """Set the scoring function."""
        self._score_fn = fn

    def score(self, transaction: dict) -> float:
        """Return the raw score for a transaction."""
        if self._score_fn:
            return self._score_fn(transaction)
        return 0.0


def ensemble_score(
    detectors: list[SimpleDetector],
    weights: list[float],
    transaction: dict,
) -> float:
    """Compute weighted ensemble fraud score.

    Steps:
    1. For each detector, call detector.score(transaction) to get raw score.
    2. Normalize: normalized = min(raw_score / detector.threshold, 1.0)
       This maps scores to [0, 1] where threshold maps to 1.0.
    3. Compute weighted average: sum(normalized_i * weight_i) / sum(weight_i)

    Args:
        detectors: list of SimpleDetector instances.
        weights: list of weights (same length as detectors).
        transaction: the transaction dict to score.

    Returns:
        Weighted average of normalized scores (float in [0, 1]).

    Raises:
        ValueError: if detectors and weights have different lengths,
                    or if detectors list is empty.
    """
    # YOUR CODE HERE (~15 lines)
    # Hints:
    # 1. Validate inputs (matching lengths, non-empty)
    # 2. For each detector/weight pair:
    #    - Get raw score from detector.score(transaction)
    #    - Normalize: min(raw_score / detector.threshold, 1.0)
    #    - Accumulate: weighted_sum += normalized * weight
    # 3. Return weighted_sum / total_weight
    raise NotImplementedError("Implement ensemble_score")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""

    # Test 1: Single detector, score at threshold -> normalized = 1.0
    d1 = SimpleDetector("zscore", threshold=3.0)
    d1.set_score_fn(lambda t: 3.0)
    result = ensemble_score([d1], [1.0], {"amount": 100})
    assert result == 1.0, f"Expected 1.0 for score at threshold, got {result}"
    print("[PASS] Score at threshold normalizes to 1.0")

    # Test 2: Score below threshold normalizes proportionally
    d2 = SimpleDetector("zscore", threshold=3.0)
    d2.set_score_fn(lambda t: 1.5)
    result = ensemble_score([d2], [1.0], {"amount": 100})
    assert abs(result - 0.5) < 0.01, f"Expected 0.5, got {result}"
    print("[PASS] Score below threshold normalizes proportionally")

    # Test 3: Weighted average of two detectors
    d_a = SimpleDetector("A", threshold=10.0)
    d_a.set_score_fn(lambda t: 10.0)  # normalized = 1.0
    d_b = SimpleDetector("B", threshold=5.0)
    d_b.set_score_fn(lambda t: 0.0)   # normalized = 0.0

    result = ensemble_score([d_a, d_b], [1.0, 1.0], {})
    assert abs(result - 0.5) < 0.01, f"Expected 0.5, got {result}"
    print(f"[PASS] Weighted average: {result:.2f}")

    # Test 4: Higher weight = more influence
    result_a_heavy = ensemble_score([d_a, d_b], [3.0, 1.0], {})
    result_b_heavy = ensemble_score([d_a, d_b], [1.0, 3.0], {})
    assert result_a_heavy > result_b_heavy, (
        f"A-heavy ({result_a_heavy:.2f}) should be > B-heavy ({result_b_heavy:.2f})"
    )
    print(f"[PASS] Weight influence: A-heavy={result_a_heavy:.2f}, B-heavy={result_b_heavy:.2f}")

    # Test 5: Mismatched lengths raises ValueError
    try:
        ensemble_score([d_a], [1.0, 2.0], {})
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Mismatched lengths raises ValueError")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
