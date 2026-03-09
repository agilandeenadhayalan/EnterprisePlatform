"""
Exercise 4: Metric Aggregator — Histogram Percentile Calculation
========================================
Implement a histogram aggregator that records observations and computes
arbitrary percentiles using sorted observations and linear interpolation.

WHY THIS MATTERS:
In production monitoring, percentiles (P50, P95, P99) are far more useful
than averages for understanding latency. The average hides outliers: if
99% of requests take 10ms and 1% take 10 seconds, the average is ~110ms
but the P99 reveals the 10-second tail. Understanding how percentiles are
computed from raw observations is foundational to SLO-based alerting.

Key concepts:
- Sorted observations: percentiles require sorting the data first
- Linear interpolation: when the desired percentile falls between two
  observations, interpolate to get a smooth estimate
- Percentile index: for N observations, the p-th percentile is at
  index (p / 100) * (N - 1) in the sorted list

YOUR TASK:
1. Implement add(value) — record an observation
2. Implement percentile(p) — compute the p-th percentile (0-100)
   using linear interpolation on sorted observations
3. Implement count() — return the number of observations
4. Implement mean() — return the arithmetic mean (0 if empty)
"""


class HistogramAggregator:
    """
    Aggregates observations and computes percentiles.

    TODO: Implement these methods:

    1. add(value: float) -> None
       Record a single observation. Append it to the internal list.

    2. percentile(p: float) -> float
       Compute the p-th percentile (p in 0-100) using linear interpolation.

       Algorithm:
       a. Sort the observations.
       b. Compute the index: k = (p / 100) * (len(sorted) - 1)
       c. f = floor(k), c = ceil(k) = f + 1
       d. If c >= len(sorted), return the last element.
       e. Otherwise: result = sorted[f] + (k - f) * (sorted[c] - sorted[f])

       Raise ValueError if no observations have been recorded.

    3. count() -> int
       Return the total number of recorded observations.

    4. mean() -> float
       Return the arithmetic mean of all observations.
       Return 0.0 if no observations have been recorded.
    """

    def __init__(self):
        self._observations = []

    def add(self, value: float) -> None:
        # YOUR CODE HERE (1 line)
        raise NotImplementedError("Implement add")

    def percentile(self, p: float) -> float:
        # YOUR CODE HERE (8 lines)
        raise NotImplementedError("Implement percentile")

    def count(self) -> int:
        # YOUR CODE HERE (1 line)
        raise NotImplementedError("Implement count")

    def mean(self) -> float:
        # YOUR CODE HERE (3 lines)
        raise NotImplementedError("Implement mean")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    agg = HistogramAggregator()

    # Test 1: add and count
    for v in [10, 20, 30, 40, 50]:
        agg.add(v)
    assert agg.count() == 5, f"Expected count 5, got {agg.count()}"
    print("[PASS] add/count: 5 observations recorded")

    # Test 2: mean
    assert agg.mean() == 30.0, f"Expected mean 30.0, got {agg.mean()}"
    print("[PASS] mean: average of [10,20,30,40,50] = 30.0")

    # Test 3: P50 (median)
    p50 = agg.percentile(50)
    assert p50 == 30.0, f"Expected P50=30.0, got {p50}"
    print(f"[PASS] percentile(50) = {p50}")

    # Test 4: P0 (minimum)
    p0 = agg.percentile(0)
    assert p0 == 10.0, f"Expected P0=10.0, got {p0}"
    print(f"[PASS] percentile(0) = {p0}")

    # Test 5: P100 (maximum)
    p100 = agg.percentile(100)
    assert p100 == 50.0, f"Expected P100=50.0, got {p100}"
    print(f"[PASS] percentile(100) = {p100}")

    # Test 6: P25 (interpolation)
    p25 = agg.percentile(25)
    assert p25 == 20.0, f"Expected P25=20.0, got {p25}"
    print(f"[PASS] percentile(25) = {p25}")

    # Test 7: empty histogram raises
    empty = HistogramAggregator()
    try:
        empty.percentile(50)
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] percentile on empty raises ValueError")

    # Test 8: empty mean returns 0
    assert empty.mean() == 0.0, f"Expected 0.0, got {empty.mean()}"
    print("[PASS] mean on empty returns 0.0")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
