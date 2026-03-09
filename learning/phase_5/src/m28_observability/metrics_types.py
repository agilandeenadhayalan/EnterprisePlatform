"""
Prometheus-style Metric Types — counters, gauges, histograms, and summaries.

WHY THIS MATTERS:
Prometheus is the de-facto standard for metrics in cloud-native systems.
Understanding how each metric type works — what operations are valid, how
buckets and quantiles are computed — is essential for writing meaningful
SLIs, SLOs, and alert rules.

Key concepts:
  - Counter: monotonically increasing value (e.g. total HTTP requests).
    Can only go up. Resets on process restart, but never via user code.
  - Gauge: value that can go up and down (e.g. current memory usage,
    in-flight requests).
  - Histogram: records observations into configurable buckets and
    computes server-side percentiles from sorted observations.
  - Summary: like Histogram but computes quantiles over a sliding
    window of the most recent observations.
"""


class Counter:
    """A monotonically increasing counter.

    Counters track cumulative values like total requests served or bytes
    sent. They can only increase (or reset to zero on process restart).
    Attempting to decrement or reset a counter raises ValueError.

    In Prometheus, counters are used with rate() to compute per-second
    rates in PromQL.
    """

    def __init__(self, name: str, labels: dict = None):
        self.name = name
        self.labels = labels or {}
        self._value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter by the given amount.

        Amount must be positive. Counters are monotonically increasing.
        Negative increments would violate the counter semantic and make
        rate() calculations incorrect.
        """
        if amount <= 0:
            raise ValueError(
                f"Counter '{self.name}': increment amount must be positive, got {amount}"
            )
        self._value += amount

    def get(self) -> float:
        """Return the current counter value."""
        return self._value

    def reset(self) -> None:
        """Counters cannot be reset by user code.

        In production, a counter reset only happens on process restart.
        Client code should never reset a counter because downstream
        rate() calculations depend on monotonicity.
        """
        raise ValueError("Counters cannot be reset")

    def to_dict(self) -> dict:
        """Serialize the counter for exposition."""
        return {
            "name": self.name,
            "type": "counter",
            "value": self._value,
            "labels": self.labels,
        }


class Gauge:
    """A gauge metric that can go up and down.

    Gauges represent a snapshot of a current value — things like
    temperature, memory usage, or the number of items in a queue.
    Unlike counters, gauges have no monotonicity constraint.
    """

    def __init__(self, name: str, labels: dict = None):
        self.name = name
        self.labels = labels or {}
        self._value: float = 0.0

    def set(self, value: float) -> None:
        """Set the gauge to an arbitrary value."""
        self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge by the given amount."""
        self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge by the given amount."""
        self._value -= amount

    def get(self) -> float:
        """Return the current gauge value."""
        return self._value

    def to_dict(self) -> dict:
        """Serialize the gauge for exposition."""
        return {
            "name": self.name,
            "type": "gauge",
            "value": self._value,
            "labels": self.labels,
        }


class Histogram:
    """A histogram that records observations into buckets.

    Histograms are the workhorse of latency measurement. Each observation
    is placed into the appropriate bucket, and cumulative bucket counts
    let you compute percentiles server-side.

    Default buckets mirror Prometheus defaults: from 5ms to 10s, plus
    +Inf. The +Inf bucket always equals the total count.

    Percentile calculation uses linear interpolation on the sorted list
    of raw observations (not bucket approximation) for accuracy.
    """

    DEFAULT_BUCKETS = [
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25,
        0.5, 1.0, 2.5, 5.0, 10.0, float("inf"),
    ]

    def __init__(self, name: str, labels: dict = None, buckets: list = None):
        self.name = name
        self.labels = labels or {}
        self._buckets = buckets or list(self.DEFAULT_BUCKETS)
        self._observations: list[float] = []

    def observe(self, value: float) -> None:
        """Record a single observation (e.g. request latency in seconds)."""
        self._observations.append(value)

    def get_count(self) -> int:
        """Return the total number of observations."""
        return len(self._observations)

    def get_sum(self) -> float:
        """Return the sum of all observed values."""
        return sum(self._observations)

    def get_mean(self) -> float:
        """Return the arithmetic mean of observations.

        Returns 0 if no observations have been recorded. This avoids
        division-by-zero errors in dashboards and alerting rules.
        """
        if not self._observations:
            return 0.0
        return self.get_sum() / self.get_count()

    def get_bucket_counts(self) -> dict:
        """Return cumulative counts for each bucket upper bound.

        Each bucket count includes all observations <= the upper bound.
        This matches Prometheus histogram_quantile() semantics where
        buckets are cumulative.
        """
        result = {}
        for upper_bound in self._buckets:
            count = sum(1 for obs in self._observations if obs <= upper_bound)
            result[upper_bound] = count
        return result

    def get_percentile(self, p: float) -> float:
        """Compute the p-th percentile using linear interpolation.

        Args:
            p: Percentile value between 0 and 100.

        Raises:
            ValueError: If no observations have been recorded.

        The algorithm sorts observations and uses linear interpolation
        between adjacent values when the index is not an integer. This
        matches numpy's default 'linear' interpolation method.
        """
        if not self._observations:
            raise ValueError(
                f"Histogram '{self.name}': cannot compute percentile with no observations"
            )
        sorted_obs = sorted(self._observations)
        n = len(sorted_obs)
        # Convert percentile to 0-1 range
        k = (p / 100.0) * (n - 1)
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_obs[-1]
        d = k - f
        return sorted_obs[f] + d * (sorted_obs[c] - sorted_obs[f])

    def to_dict(self) -> dict:
        """Serialize the histogram for exposition."""
        return {
            "name": self.name,
            "type": "histogram",
            "count": self.get_count(),
            "sum": self.get_sum(),
            "buckets": self.get_bucket_counts(),
            "labels": self.labels,
        }


class Summary:
    """A summary metric that computes quantiles over a sliding window.

    Summaries differ from histograms in that quantiles are computed
    client-side over a configurable window of recent observations.

    The _max_age_observations parameter limits how many recent
    observations are used for quantile computation, simulating a
    time-based sliding window.

    WHY SLIDING WINDOW:
    In production, you care about recent latency, not the all-time
    average. A 5-minute window shows current behavior, while all-time
    metrics are dominated by historical data.
    """

    def __init__(self, name: str, labels: dict = None, max_age_observations: int = 1000):
        self.name = name
        self.labels = labels or {}
        self._observations: list[float] = []
        self._max_age_observations = max_age_observations

    def observe(self, value: float) -> None:
        """Record a single observation."""
        self._observations.append(value)

    def get_quantile(self, q: float) -> float:
        """Compute the q-th quantile over the sliding window.

        Args:
            q: Quantile value between 0.0 and 1.0 (e.g. 0.5 for median).

        Uses only the last _max_age_observations entries to approximate
        a time-windowed quantile. Returns the interpolated value using
        the same algorithm as Histogram.get_percentile().
        """
        window = self._observations[-self._max_age_observations:]
        if not window:
            return 0.0
        sorted_obs = sorted(window)
        n = len(sorted_obs)
        k = q * (n - 1)
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_obs[-1]
        d = k - f
        return sorted_obs[f] + d * (sorted_obs[c] - sorted_obs[f])

    def get_count(self) -> int:
        """Return the total number of observations (all time)."""
        return len(self._observations)

    def get_sum(self) -> float:
        """Return the sum of all observations (all time)."""
        return sum(self._observations)
