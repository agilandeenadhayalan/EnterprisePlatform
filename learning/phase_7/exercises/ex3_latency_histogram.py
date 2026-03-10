"""
Exercise 3: Latency Histogram Percentile Calculation
========================================
Implement percentile(p) using linear interpolation on sorted samples.

WHY THIS MATTERS:
Average latency hides the tail. If your average is 50ms but your p99
is 5000ms, 1% of users are furious. Percentile calculation from raw
samples is the foundation of performance monitoring.

Linear interpolation gives smoother results than nearest-rank for
small datasets — instead of jumping between adjacent values, you
interpolate between them based on the fractional rank.

YOUR TASK:
Implement percentile(p) that:
  1. Sorts the samples
  2. Computes the fractional rank: rank = (p / 100) * (n - 1)
  3. Interpolates between floor(rank) and ceil(rank)
"""


class SimpleHistogram:
    """A simple histogram that stores raw samples for percentile calculation."""

    def __init__(self):
        self._samples: list[float] = []

    def add_sample(self, value: float) -> None:
        """Add a single latency sample."""
        self._samples.append(value)

    def add_samples(self, values: list[float]) -> None:
        """Add multiple samples at once."""
        self._samples.extend(values)

    @property
    def count(self) -> int:
        """Number of recorded samples."""
        return len(self._samples)

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile (0-100) using linear interpolation.

        YOUR TASK:
        1. If no samples, return 0.0
        2. Sort the samples
        3. Compute fractional rank: rank = (p / 100) * (n - 1)
        4. lower_idx = floor(rank), upper_idx = min(lower_idx + 1, n - 1)
        5. fraction = rank - lower_idx
        6. Return: sorted[lower] + fraction * (sorted[upper] - sorted[lower])

        This gives exact results at the boundaries (p=0 -> min, p=100 -> max)
        and smoothly interpolates between adjacent values.
        """
        # YOUR CODE HERE (~8 lines)
        raise NotImplementedError("Implement percentile")


# ── Verification ──


def test_p50():
    """Median of [10, 20, 30, 40, 50] is 30."""
    h = SimpleHistogram()
    h.add_samples([10, 20, 30, 40, 50])
    result = h.percentile(50)
    assert abs(result - 30) < 1, f"p50 should be ~30, got {result}"
    print("[PASS] test_p50")


def test_p95():
    """p95 of 1..100 should be ~95."""
    h = SimpleHistogram()
    h.add_samples(list(range(1, 101)))
    result = h.percentile(95)
    assert 93 < result < 97, f"p95 should be ~95, got {result}"
    print("[PASS] test_p95")


def test_p99():
    """p99 of 1..100 should be ~99."""
    h = SimpleHistogram()
    h.add_samples(list(range(1, 101)))
    result = h.percentile(99)
    assert 97 < result < 101, f"p99 should be ~99, got {result}"
    print("[PASS] test_p99")


def test_single_sample():
    """Single sample is all percentiles."""
    h = SimpleHistogram()
    h.add_sample(42.0)
    assert h.percentile(0) == 42.0
    assert h.percentile(50) == 42.0
    assert h.percentile(100) == 42.0
    print("[PASS] test_single_sample")


def test_large_dataset():
    """p50 of 10000 uniform samples is ~5000."""
    h = SimpleHistogram()
    h.add_samples(list(range(1, 10001)))
    result = h.percentile(50)
    assert 4900 < result < 5100, f"p50 should be ~5000, got {result}"
    print("[PASS] test_large_dataset")


def test_even_distribution():
    """Interpolation works for even-length lists."""
    h = SimpleHistogram()
    h.add_samples([10, 20, 30, 40])
    result = h.percentile(50)
    assert abs(result - 25) < 1, f"p50 of [10,20,30,40] should be ~25, got {result}"
    print("[PASS] test_even_distribution")


if __name__ == "__main__":
    test_p50()
    test_p95()
    test_p99()
    test_single_sample()
    test_large_dataset()
    test_even_distribution()
    print("\nAll checks passed!")
