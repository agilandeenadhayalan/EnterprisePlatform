"""
Prometheus-style metrics primitives for application instrumentation.

This module provides three core metric types that mirror the Prometheus data
model, enabling services to expose operational measurements in a standardized
way. All implementations are pure Python with no external dependencies.

Metric Types
------------
- **Counter**: A monotonically increasing value (e.g., total requests served,
  errors encountered). Counters can only go up -- they never decrease during
  normal operation. This makes them ideal for tracking cumulative totals that
  are then analyzed via rate() or increase() functions in a monitoring system.

- **Gauge**: A value that can go up or down (e.g., current queue depth, active
  connections, memory usage). Gauges represent a snapshot of some current state
  and are sampled at scrape time.

- **Histogram**: Tracks the distribution of observed values (e.g., request
  latencies, response sizes). Values are sorted into configurable buckets and
  support percentile calculations. This allows operators to answer questions
  like "what is the 99th percentile latency?" without storing every data point
  in a time-series database.

Usage Example
-------------
    client = MetricsClient()

    # Track total HTTP requests by method and status
    req_counter = client.counter("http_requests_total", {"method": "GET", "status": "200"})
    req_counter.inc()

    # Track in-flight requests
    inflight = client.gauge("http_inflight_requests")
    inflight.inc()   # request starts
    inflight.dec()   # request ends

    # Track request latency distribution
    latency = client.histogram("http_request_duration_seconds")
    latency.observe(0.042)

    # Export all metrics for scraping
    all_metrics = client.collect()
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional


class Counter:
    """A monotonically increasing counter metric.

    Counters track cumulative values that only go up: total requests, bytes
    transmitted, errors encountered, etc. The primary operations are ``inc()``
    to add to the counter and ``get()`` to read the current value.

    Attempting to increment by a negative amount raises ``ValueError`` because
    counters must be monotonic -- this invariant is what allows monitoring
    systems to reliably compute rates and detect counter resets.

    Parameters
    ----------
    name : str
        The metric name, following Prometheus naming conventions
        (e.g., ``http_requests_total``).
    labels : dict, optional
        Key-value pairs that identify a specific dimensional slice of the
        metric (e.g., ``{"method": "GET", "status": "200"}``).
    """

    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.labels = labels or {}
        self._value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter by the given amount.

        Parameters
        ----------
        amount : float
            The value to add. Must be positive.

        Raises
        ------
        ValueError
            If ``amount`` is negative. Counters are monotonically increasing.
        """
        if amount < 0:
            raise ValueError(
                f"Counter '{self.name}' cannot be incremented by a negative "
                f"amount ({amount}). Counters are monotonically increasing."
            )
        self._value += amount

    def get(self) -> float:
        """Return the current counter value."""
        return self._value

    def reset(self) -> None:
        """Reset is not supported on counters.

        Raises
        ------
        ValueError
            Always. Counters should never be reset in production; a reset
            breaks rate calculations in monitoring systems.
        """
        raise ValueError(
            f"Counter '{self.name}' cannot be reset. Counters are "
            "monotonically increasing and resetting them breaks rate "
            "calculations in monitoring systems."
        )

    def to_dict(self) -> Dict:
        """Serialize the counter to a dictionary for export.

        Returns
        -------
        dict
            A dictionary containing the metric type, name, labels, and value.
        """
        return {
            "type": "counter",
            "name": self.name,
            "labels": self.labels,
            "value": self._value,
        }

    def __repr__(self) -> str:
        return f"Counter(name={self.name!r}, labels={self.labels!r}, value={self._value})"


class Gauge:
    """A metric that represents a single numerical value that can go up or down.

    Gauges are typically used for measured values like current temperature,
    memory usage, active connections, or queue depth -- values that fluctuate
    during normal operation.

    Unlike counters, gauges have no monotonicity constraint and support both
    ``inc()`` and ``dec()`` operations as well as direct ``set()`` calls.

    Parameters
    ----------
    name : str
        The metric name (e.g., ``process_memory_bytes``).
    labels : dict, optional
        Dimensional label key-value pairs.
    """

    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.labels = labels or {}
        self._value: float = 0.0

    def set(self, value: float) -> None:
        """Set the gauge to an arbitrary value.

        Parameters
        ----------
        value : float
            The new value for the gauge.
        """
        self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge by the given amount.

        Parameters
        ----------
        amount : float
            The value to add (can be negative, but prefer ``dec()`` for clarity).
        """
        self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge by the given amount.

        Parameters
        ----------
        amount : float
            The value to subtract.
        """
        self._value -= amount

    def get(self) -> float:
        """Return the current gauge value."""
        return self._value

    def to_dict(self) -> Dict:
        """Serialize the gauge to a dictionary for export.

        Returns
        -------
        dict
            A dictionary containing the metric type, name, labels, and value.
        """
        return {
            "type": "gauge",
            "name": self.name,
            "labels": self.labels,
            "value": self._value,
        }

    def __repr__(self) -> str:
        return f"Gauge(name={self.name!r}, labels={self.labels!r}, value={self._value})"


class Histogram:
    """Tracks the statistical distribution of observed values.

    Histograms sample observations (usually things like request durations or
    response sizes) and count them in configurable buckets. They also provide
    a total count and sum of observed values, enabling calculation of averages
    and percentiles.

    The default bucket boundaries are tuned for typical HTTP request latencies
    measured in seconds, following the Prometheus convention. Custom bucket
    boundaries can be provided for other use cases (e.g., response sizes in
    bytes or queue wait times).

    Bucket Semantics
    ----------------
    Each bucket counts how many observations fall at or below its upper
    boundary. For boundaries ``[0.1, 0.5, 1.0]`` and observations
    ``[0.05, 0.3, 0.8]``:

    - ``le=0.1``: 1  (only 0.05)
    - ``le=0.5``: 2  (0.05 and 0.3)
    - ``le=1.0``: 3  (all three)

    Parameters
    ----------
    name : str
        The metric name (e.g., ``http_request_duration_seconds``).
    labels : dict, optional
        Dimensional label key-value pairs.
    buckets : list of float, optional
        Upper boundary values for histogram buckets. Defaults to standard
        Prometheus latency buckets.
    """

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> None:
        self.name = name
        self.labels = labels or {}
        self._buckets = sorted(buckets) if buckets else list(self.DEFAULT_BUCKETS)
        self._observations: List[float] = []

    def observe(self, value: float) -> None:
        """Record an observed value in the histogram.

        Parameters
        ----------
        value : float
            The observed measurement (e.g., request duration in seconds).
        """
        self._observations.append(value)

    def get_count(self) -> int:
        """Return the total number of observations recorded."""
        return len(self._observations)

    def get_sum(self) -> float:
        """Return the sum of all observed values."""
        return sum(self._observations)

    def get_mean(self) -> float:
        """Return the arithmetic mean of observed values.

        Returns
        -------
        float
            The mean, or 0.0 if no observations have been recorded.
        """
        if not self._observations:
            return 0.0
        return self.get_sum() / self.get_count()

    def get_bucket_counts(self) -> Dict[float, int]:
        """Return the cumulative count of observations per bucket boundary.

        Each bucket's count represents the number of observations whose value
        is less than or equal to the bucket's upper boundary. Buckets are
        cumulative: the count for a higher boundary always includes the count
        of all lower boundaries.

        Returns
        -------
        dict
            Mapping of bucket upper boundary (float) to cumulative count (int).
        """
        counts: Dict[float, int] = {}
        for boundary in self._buckets:
            counts[boundary] = sum(1 for obs in self._observations if obs <= boundary)
        return counts

    def get_percentile(self, p: float) -> float:
        """Calculate the p-th percentile from recorded observations.

        Uses the nearest-rank method: the percentile value is the smallest
        observation such that at least ``p`` percent of the data falls at
        or below it.

        Parameters
        ----------
        p : float
            The desired percentile, between 0 and 100 inclusive.

        Returns
        -------
        float
            The percentile value.

        Raises
        ------
        ValueError
            If ``p`` is outside the range [0, 100] or no observations exist.
        """
        if not self._observations:
            raise ValueError("Cannot compute percentile with no observations.")
        if p < 0 or p > 100:
            raise ValueError(f"Percentile must be between 0 and 100, got {p}.")

        sorted_obs = sorted(self._observations)
        if p == 0:
            return sorted_obs[0]
        index = math.ceil(p / 100.0 * len(sorted_obs)) - 1
        return sorted_obs[index]

    def to_dict(self) -> Dict:
        """Serialize the histogram to a dictionary for export.

        Returns
        -------
        dict
            A dictionary containing the metric type, name, labels, bucket
            counts, observation count, sum, and mean.
        """
        return {
            "type": "histogram",
            "name": self.name,
            "labels": self.labels,
            "buckets": self.get_bucket_counts(),
            "count": self.get_count(),
            "sum": self.get_sum(),
            "mean": self.get_mean(),
        }

    def __repr__(self) -> str:
        return (
            f"Histogram(name={self.name!r}, labels={self.labels!r}, "
            f"observations={self.get_count()})"
        )


class MetricsClient:
    """Central registry for creating and collecting application metrics.

    The ``MetricsClient`` serves as a single point of access for all metrics
    within a service. It manages the lifecycle of counters, gauges, and
    histograms, ensuring that requesting the same metric name and labels
    returns the same instance (avoiding duplicate metric registration).

    In a typical deployment, each service creates one ``MetricsClient`` at
    startup and passes it to subsystems that need to record measurements.
    A metrics scraper (e.g., Prometheus) periodically calls ``collect()``
    to gather all current metric values.

    Usage Example
    -------------
        client = MetricsClient()

        # Register and use metrics
        requests = client.counter("http_requests_total", {"method": "GET"})
        requests.inc()

        queue = client.gauge("queue_depth")
        queue.set(42)

        latency = client.histogram("request_duration_seconds")
        latency.observe(0.123)

        # Scrape all metrics
        snapshot = client.collect()
    """

    def __init__(self) -> None:
        self._metrics: Dict[str, object] = {}

    def _key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Build a unique key from metric name and sorted label pairs."""
        label_str = ""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}:{label_str}"

    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Create or retrieve a counter metric.

        Parameters
        ----------
        name : str
            The counter name.
        labels : dict, optional
            Dimensional labels.

        Returns
        -------
        Counter
            The counter instance (created on first call, retrieved on
            subsequent calls with the same name and labels).
        """
        key = self._key(name, labels)
        if key not in self._metrics:
            self._metrics[key] = Counter(name, labels)
        return self._metrics[key]  # type: ignore[return-value]

    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Create or retrieve a gauge metric.

        Parameters
        ----------
        name : str
            The gauge name.
        labels : dict, optional
            Dimensional labels.

        Returns
        -------
        Gauge
            The gauge instance.
        """
        key = self._key(name, labels)
        if key not in self._metrics:
            self._metrics[key] = Gauge(name, labels)
        return self._metrics[key]  # type: ignore[return-value]

    def histogram(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Create or retrieve a histogram metric.

        Parameters
        ----------
        name : str
            The histogram name.
        labels : dict, optional
            Dimensional labels.
        buckets : list of float, optional
            Custom bucket boundaries. Only used when creating a new histogram.

        Returns
        -------
        Histogram
            The histogram instance.
        """
        key = self._key(name, labels)
        if key not in self._metrics:
            self._metrics[key] = Histogram(name, labels, buckets)
        return self._metrics[key]  # type: ignore[return-value]

    def collect(self) -> List[Dict]:
        """Export all registered metrics as a list of dictionaries.

        This is the primary method called by a metrics scraper. Each metric
        is serialized via its ``to_dict()`` method.

        Returns
        -------
        list of dict
            One dictionary per registered metric.
        """
        return [metric.to_dict() for metric in self._metrics.values()]  # type: ignore[union-attr]

    def get(self, name: str) -> object:
        """Look up a metric by name (without labels).

        If multiple metrics share the same name but have different labels,
        this returns the first match found. For precise lookups, use
        ``counter()``, ``gauge()``, or ``histogram()`` with the exact labels.

        Parameters
        ----------
        name : str
            The metric name to search for.

        Returns
        -------
        object or None
            The metric instance, or ``None`` if not found.
        """
        for key, metric in self._metrics.items():
            if key.startswith(f"{name}:"):
                return metric
        return None

    def __repr__(self) -> str:
        return f"MetricsClient(metrics={len(self._metrics)})"
