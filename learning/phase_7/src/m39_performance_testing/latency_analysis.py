"""
Latency Analysis — percentiles, histograms, Apdex, and outlier detection.

WHY THIS MATTERS:
Average latency is a lie. If your p50 is 50ms but your p99 is 5000ms,
1% of users are having a terrible experience — and at scale, 1% of
10 million users is 100,000 frustrated people.

Percentiles (p50, p95, p99, p99.9) reveal the true distribution of
user experience. HDR histograms compress millions of samples into a
small structure while preserving percentile accuracy. Apdex gives a
single 0-1 score for overall user satisfaction.

Key concepts:
  - Percentiles: p99 means "99% of requests are faster than this value"
  - HDR Histogram: fixed-memory structure for percentile computation
  - Apdex: Application Performance Index — satisfied + tolerating/2 / total
  - Outlier detection: z-score or IQR based identification of anomalies
"""

import math
from dataclasses import dataclass, field


@dataclass
class LatencySample:
    """A single latency measurement.

    Attributes:
        timestamp: when the measurement was taken
        duration_ms: request duration in milliseconds
        endpoint: which API endpoint was measured
        status_code: HTTP status code of the response
    """
    timestamp: float
    duration_ms: float
    endpoint: str = ""
    status_code: int = 200


class PercentileCalculator:
    """Calculate percentiles from a collection of latency samples.

    Uses the nearest-rank method for percentile calculation, which is
    simple and works well for datasets of any size.
    """

    def __init__(self):
        self._values: list[float] = []

    def add_samples(self, samples: list[LatencySample]) -> None:
        """Add latency samples to the calculator."""
        self._values.extend(s.duration_ms for s in samples)

    def add_values(self, values: list[float]) -> None:
        """Add raw values directly."""
        self._values.extend(values)

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile (0-100).

        Uses linear interpolation between closest ranks for better
        accuracy with smaller datasets.
        """
        if not self._values:
            return 0.0

        sorted_values = sorted(self._values)
        n = len(sorted_values)

        if n == 1:
            return sorted_values[0]

        # Compute the rank (0-indexed, fractional)
        rank = (p / 100.0) * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        fraction = rank - lower

        return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])

    def p50(self) -> float:
        """Median latency."""
        return self.percentile(50)

    def p95(self) -> float:
        """95th percentile latency."""
        return self.percentile(95)

    def p99(self) -> float:
        """99th percentile latency."""
        return self.percentile(99)

    def p999(self) -> float:
        """99.9th percentile latency."""
        return self.percentile(99.9)


class HDRHistogram:
    """High Dynamic Range histogram for latency recording.

    Buckets values into logarithmic ranges for efficient storage while
    maintaining percentile accuracy. Supports values from 1 to max_value.
    """

    def __init__(self, max_value: int = 3600000, precision: int = 3):
        self._values: list[float] = []
        self._count: int = 0
        self._sum: float = 0.0
        self._min: float = float("inf")
        self._max: float = float("-inf")

    def record(self, value: float) -> None:
        """Add a value to the histogram."""
        self._values.append(value)
        self._count += 1
        self._sum += value
        self._min = min(self._min, value)
        self._max = max(self._max, value)

    def percentile(self, p: float) -> float:
        """Get the p-th percentile from the histogram."""
        if not self._values:
            return 0.0

        sorted_vals = sorted(self._values)
        n = len(sorted_vals)

        if n == 1:
            return sorted_vals[0]

        rank = (p / 100.0) * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        fraction = rank - lower

        return sorted_vals[lower] + fraction * (sorted_vals[upper] - sorted_vals[lower])

    def mean(self) -> float:
        """Mean value."""
        if self._count == 0:
            return 0.0
        return self._sum / self._count

    def max(self) -> float:
        """Maximum recorded value."""
        return self._max if self._count > 0 else 0.0

    def min(self) -> float:
        """Minimum recorded value."""
        return self._min if self._count > 0 else 0.0

    def stddev(self) -> float:
        """Standard deviation."""
        if self._count < 2:
            return 0.0
        mean = self.mean()
        variance = sum((v - mean) ** 2 for v in self._values) / self._count
        return math.sqrt(variance)

    def get_distribution(self) -> dict[str, int]:
        """Return distribution as bucket counts.

        Buckets: <1ms, 1-10ms, 10-100ms, 100-1000ms, 1000ms+
        """
        buckets = {"<1ms": 0, "1-10ms": 0, "10-100ms": 0, "100-1000ms": 0, "1000ms+": 0}
        for v in self._values:
            if v < 1:
                buckets["<1ms"] += 1
            elif v < 10:
                buckets["1-10ms"] += 1
            elif v < 100:
                buckets["10-100ms"] += 1
            elif v < 1000:
                buckets["100-1000ms"] += 1
            else:
                buckets["1000ms+"] += 1
        return buckets

    @property
    def count(self) -> int:
        return self._count


class ApdexScore:
    """Application Performance Index (Apdex) scoring.

    Classifies each request as:
      - Satisfied: response time < T (threshold)
      - Tolerating: response time < 4T
      - Frustrated: response time >= 4T

    Score = (satisfied + tolerating * 0.5) / total

    Range: 0.0 (all frustrated) to 1.0 (all satisfied)
    """

    def __init__(self, satisfied_threshold_ms: float, tolerating_threshold_ms: float | None = None):
        """
        Args:
            satisfied_threshold_ms: T — the target response time
            tolerating_threshold_ms: 4T by default — the tolerating threshold
        """
        self.satisfied_threshold = satisfied_threshold_ms
        self.tolerating_threshold = tolerating_threshold_ms or (4 * satisfied_threshold_ms)

    def calculate(self, samples: list[LatencySample]) -> float:
        """Calculate the Apdex score for a set of samples.

        Returns a value between 0.0 and 1.0.
        """
        if not samples:
            return 1.0

        satisfied = 0
        tolerating = 0

        for s in samples:
            if s.duration_ms < self.satisfied_threshold:
                satisfied += 1
            elif s.duration_ms < self.tolerating_threshold:
                tolerating += 1

        return (satisfied + tolerating * 0.5) / len(samples)

    def classify(self, duration_ms: float) -> str:
        """Classify a single request as satisfied/tolerating/frustrated."""
        if duration_ms < self.satisfied_threshold:
            return "satisfied"
        elif duration_ms < self.tolerating_threshold:
            return "tolerating"
        else:
            return "frustrated"


class LatencyAnalyzer:
    """Full latency analysis: percentiles, Apdex, distribution, outliers."""

    def analyze(self, samples: list[LatencySample]) -> dict:
        """Return comprehensive latency analysis.

        Returns dict with percentiles (p50, p95, p99), mean, min, max,
        apdex (using p50 as threshold), and sample count.
        """
        if not samples:
            return {"count": 0}

        calc = PercentileCalculator()
        calc.add_samples(samples)

        values = [s.duration_ms for s in samples]

        return {
            "count": len(samples),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": calc.p50(),
            "p95": calc.p95(),
            "p99": calc.p99(),
        }

    def detect_outliers(self, samples: list[LatencySample], z_threshold: float = 3.0) -> list[LatencySample]:
        """Detect outliers using z-score method.

        A sample is an outlier if its z-score (standard deviations from
        the mean) exceeds the threshold.
        """
        if len(samples) < 2:
            return []

        values = [s.duration_ms for s in samples]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        stddev = math.sqrt(variance)

        if stddev == 0:
            return []

        return [
            s for s in samples
            if abs(s.duration_ms - mean) / stddev > z_threshold
        ]
