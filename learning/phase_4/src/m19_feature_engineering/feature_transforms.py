"""
Feature Transforms
==================

Raw data rarely goes directly into ML models. Feature transforms convert
raw values into forms that are more useful for learning:

**BucketTransform**: Converts continuous values into discrete categories.
  Example: fare_amount -> "low" / "medium" / "high"
  Why: Helps models learn non-linear boundaries and reduces sensitivity
  to outliers.

**LogTransform**: Applies log(1 + x) to compress right-skewed distributions.
  Example: trip_fare values ranging from $5 to $500 become more uniform.
  Why: Many ML algorithms work better when features have similar scales
  and are roughly normally distributed.

**InteractionFeature**: Combines two features to capture their joint effect.
  Example: distance * surge_multiplier captures the actual fare impact
  that neither feature alone represents.

**WindowAggregate**: Computes rolling statistics (mean, std, min, max) over
  a sliding window of recent values.
  Example: avg_speed over last 5 trips helps detect unusual driving patterns.
"""

from __future__ import annotations

import math


class BucketTransform:
    """Bins continuous values into discrete buckets.

    Boundaries define the edges between buckets. For boundaries [10, 50, 100]:
    - value < 10      -> bucket 0 (or label[0])
    - 10 <= value < 50 -> bucket 1 (or label[1])
    - 50 <= value < 100 -> bucket 2 (or label[2])
    - value >= 100     -> bucket 3 (or label[3])

    This is useful for converting continuous features into categorical ones,
    which can help tree-based models find optimal split points.
    """

    def __init__(
        self,
        boundaries: list[float],
        labels: list[str] | None = None,
    ) -> None:
        """Initialize the bucket transform.

        Args:
            boundaries: Sorted list of boundary values.
            labels: Optional human-readable labels for each bucket.
                    Must have len(boundaries) + 1 elements.

        Raises:
            ValueError: If boundaries are empty, not sorted, or labels
                        have wrong length.
        """
        if not boundaries:
            raise ValueError("boundaries must not be empty")

        for i in range(1, len(boundaries)):
            if boundaries[i] <= boundaries[i - 1]:
                raise ValueError("boundaries must be strictly increasing")

        if labels is not None and len(labels) != len(boundaries) + 1:
            raise ValueError(
                f"labels must have {len(boundaries) + 1} elements, "
                f"got {len(labels)}"
            )

        self.boundaries = list(boundaries)
        self.labels = labels

    def transform(self, value: float) -> str:
        """Assign a single value to its bucket.

        Returns:
            The bucket label (if labels provided) or 'bucket_N' string.
        """
        bucket_idx = 0
        for boundary in self.boundaries:
            if value < boundary:
                break
            bucket_idx += 1

        if self.labels is not None:
            return self.labels[bucket_idx]
        return f"bucket_{bucket_idx}"

    def transform_batch(self, values: list[float]) -> list[str]:
        """Assign multiple values to their buckets."""
        return [self.transform(v) for v in values]


class LogTransform:
    """Log(1 + x) transform for right-skewed distributions.

    Many real-world features (fares, distances, wait times) follow
    right-skewed distributions where most values are small but a few
    are very large. Log transform compresses these distributions,
    making them more suitable for ML models that assume roughly
    normal input distributions.

    We use log(1 + x) instead of log(x) to handle zero values safely.
    """

    def transform(self, value: float) -> float:
        """Apply log(1 + x) transform.

        Args:
            value: Non-negative input value.

        Returns:
            The transformed value.

        Raises:
            ValueError: If value is negative.
        """
        if value < 0:
            raise ValueError(f"LogTransform requires non-negative values, got {value}")
        return math.log1p(value)

    def inverse(self, value: float) -> float:
        """Apply inverse transform: exp(x) - 1.

        Useful for converting predictions back to the original scale.
        """
        return math.expm1(value)

    def transform_batch(self, values: list[float]) -> list[float]:
        """Transform a list of values."""
        return [self.transform(v) for v in values]


class InteractionFeature:
    """Creates interaction features by combining two input features.

    Sometimes the relationship between features matters more than the
    features themselves. For example:
    - distance * surge_multiplier = effective_fare_driver
    - hour_of_day * is_weekend = time_context

    Supported operations: 'multiply', 'add', 'subtract', 'divide', 'ratio'.
    'ratio' is like divide but returns 0.0 when the denominator is 0.
    """

    SUPPORTED_OPS = ("multiply", "add", "subtract", "divide", "ratio")

    def __init__(
        self,
        feature_a: str,
        feature_b: str,
        operation: str = "multiply",
    ) -> None:
        if operation not in self.SUPPORTED_OPS:
            raise ValueError(
                f"operation must be one of {self.SUPPORTED_OPS}, got {operation!r}"
            )
        self.feature_a = feature_a
        self.feature_b = feature_b
        self.operation = operation

    def compute(self, row: dict) -> float:
        """Compute the interaction feature from a data row.

        Args:
            row: Dict containing both feature_a and feature_b values.

        Returns:
            The computed interaction value.

        Raises:
            KeyError: If a required feature is missing from the row.
            ZeroDivisionError: If dividing by zero (use 'ratio' for safe division).
        """
        a = row[self.feature_a]
        b = row[self.feature_b]

        if self.operation == "multiply":
            return a * b
        elif self.operation == "add":
            return a + b
        elif self.operation == "subtract":
            return a - b
        elif self.operation == "divide":
            return a / b
        elif self.operation == "ratio":
            return a / b if b != 0 else 0.0
        # Should never reach here due to __init__ validation
        raise ValueError(f"Unknown operation: {self.operation}")  # pragma: no cover

    @property
    def name(self) -> str:
        """Generate a descriptive name for this interaction feature."""
        return f"{self.feature_a}_{self.operation}_{self.feature_b}"


class WindowAggregate:
    """Computes rolling window aggregates over a sequence of values.

    Rolling aggregates capture recent trends and patterns:
    - mean: average behavior over recent history
    - std: volatility / consistency measure
    - min/max: extreme values in the window
    - sum: cumulative activity level

    For positions where the window extends before the start of data,
    the aggregate is computed over the available values. If no values
    are available, None is returned.
    """

    SUPPORTED_FUNCS = ("mean", "std", "min", "max", "sum")

    def __init__(self, window_size: int, agg_func: str = "mean") -> None:
        """Initialize the window aggregate.

        Args:
            window_size: Number of values in the rolling window.
            agg_func: Aggregation function to apply.
        """
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        if agg_func not in self.SUPPORTED_FUNCS:
            raise ValueError(
                f"agg_func must be one of {self.SUPPORTED_FUNCS}, got {agg_func!r}"
            )
        self.window_size = window_size
        self.agg_func = agg_func

    def compute(self, values: list[float]) -> list[float | None]:
        """Compute rolling aggregate over the values list.

        For each position i, computes the aggregate over
        values[max(0, i - window_size + 1) : i + 1].

        Returns:
            List of aggregated values, same length as input.
            Returns None for positions with no data.
        """
        if not values:
            return []

        results: list[float | None] = []
        for i in range(len(values)):
            start = max(0, i - self.window_size + 1)
            window = values[start: i + 1]

            if not window:
                results.append(None)
                continue

            results.append(self._aggregate(window))

        return results

    def _aggregate(self, window: list[float]) -> float:
        """Apply the aggregation function to a window of values."""
        if self.agg_func == "mean":
            return sum(window) / len(window)
        elif self.agg_func == "sum":
            return sum(window)
        elif self.agg_func == "min":
            return min(window)
        elif self.agg_func == "max":
            return max(window)
        elif self.agg_func == "std":
            if len(window) < 2:
                return 0.0
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
            return math.sqrt(variance)
        raise ValueError(f"Unknown agg_func: {self.agg_func}")  # pragma: no cover
