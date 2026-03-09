"""
Data Profiling — Understanding Your Data
===========================================

Data profiling analyzes a dataset to produce statistics that help
you understand its structure, quality, and distribution.

WHY PROFILE:
- Discover data quality issues before they break your pipeline.
- Understand the shape of data for modeling decisions.
- Set realistic thresholds for quality rules.
- Detect schema drift (new columns, changed types).

STATISTICS COMPUTED:
- **Count**: Total number of records.
- **Null count/percentage**: How many values are missing.
- **Distinct count**: Cardinality of the column.
- **Min/Max/Mean/Median/StdDev**: Numeric distribution.
- **Histogram**: Frequency distribution of values.
- **Percentiles**: Values at P25, P50, P75, P90, P99.

CARDINALITY ESTIMATION:
For very large datasets, exact cardinality is expensive.
HyperLogLog provides an approximate count using much less memory.
This simulation shows the concept (real HLL uses hash bucketing).
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnProfile:
    """Statistical profile for a single column."""
    column_name: str
    count: int
    null_count: int
    null_pct: float
    distinct_count: int
    dtype: str
    min_value: Any = None
    max_value: Any = None
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None


@dataclass
class DistributionResult:
    """Distribution analysis of a numeric column."""
    column_name: str
    histogram: dict[str, int]  # bucket_label -> count
    percentiles: dict[str, float]  # p25, p50, p75, p90, p99
    skewness: float


class DataProfiler:
    """
    Analyzes a dataset and produces column-level statistics.

    Accepts a list of dictionaries (records) and profiles each column
    found in the data.
    """

    def __init__(self, data: list[dict[str, Any]]) -> None:
        if not data:
            raise ValueError("Cannot profile empty dataset")
        self._data = data
        self._columns = self._discover_columns()

    def _discover_columns(self) -> list[str]:
        """Find all unique column names across all records."""
        columns: set[str] = set()
        for record in self._data:
            columns.update(record.keys())
        return sorted(columns)

    @property
    def columns(self) -> list[str]:
        return list(self._columns)

    @property
    def row_count(self) -> int:
        return len(self._data)

    def profile_column(self, column: str) -> ColumnProfile:
        """Generate a statistical profile for a single column."""
        values = [r.get(column) for r in self._data]
        non_null = [v for v in values if v is not None]
        null_count = len(values) - len(non_null)
        null_pct = round(null_count / len(values) * 100, 2) if values else 0.0
        distinct = len(set(str(v) for v in non_null))

        # Detect type
        dtype = self._detect_type(non_null)

        profile = ColumnProfile(
            column_name=column,
            count=len(values),
            null_count=null_count,
            null_pct=null_pct,
            distinct_count=distinct,
            dtype=dtype,
        )

        if non_null:
            try:
                profile.min_value = min(non_null)
                profile.max_value = max(non_null)
            except TypeError:
                pass

        if dtype in ("int", "float") and non_null:
            numeric = [float(v) for v in non_null]
            profile.mean = round(sum(numeric) / len(numeric), 4)
            profile.median = self._median(numeric)
            profile.std_dev = self._std_dev(numeric)

        return profile

    def profile_all(self) -> list[ColumnProfile]:
        """Profile all columns in the dataset."""
        return [self.profile_column(col) for col in self._columns]

    @staticmethod
    def _detect_type(values: list[Any]) -> str:
        """Detect the predominant type of values."""
        if not values:
            return "unknown"
        type_counts: dict[str, int] = {}
        for v in values:
            t = type(v).__name__
            type_counts[t] = type_counts.get(t, 0) + 1
        return max(type_counts, key=type_counts.get)  # type: ignore

    @staticmethod
    def _median(values: list[float]) -> float:
        """Compute median of a list of numbers."""
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 1:
            return round(sorted_vals[n // 2], 4)
        return round((sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2, 4)

    @staticmethod
    def _std_dev(values: list[float]) -> float:
        """Compute population standard deviation."""
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        return round(math.sqrt(variance), 4)


class DistributionAnalysis:
    """
    Analyzes the distribution of a numeric column.

    Produces histograms, percentiles, and skewness measures.
    """

    @staticmethod
    def histogram(values: list[float], num_buckets: int = 10) -> dict[str, int]:
        """Create a histogram with equal-width buckets."""
        if not values:
            return {}

        min_val = min(values)
        max_val = max(values)

        if min_val == max_val:
            return {f"[{min_val}, {max_val}]": len(values)}

        bucket_width = (max_val - min_val) / num_buckets
        buckets: dict[str, int] = {}

        for i in range(num_buckets):
            low = min_val + i * bucket_width
            high = min_val + (i + 1) * bucket_width
            label = f"[{round(low, 2)}, {round(high, 2)})"
            buckets[label] = 0

        for v in values:
            idx = min(int((v - min_val) / bucket_width), num_buckets - 1)
            low = min_val + idx * bucket_width
            high = min_val + (idx + 1) * bucket_width
            label = f"[{round(low, 2)}, {round(high, 2)})"
            buckets[label] = buckets.get(label, 0) + 1

        return buckets

    @staticmethod
    def percentiles(values: list[float]) -> dict[str, float]:
        """Compute P25, P50, P75, P90, P99 percentiles."""
        if not values:
            return {}

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def _percentile(p: float) -> float:
            idx = (p / 100) * (n - 1)
            lower = int(idx)
            upper = min(lower + 1, n - 1)
            fraction = idx - lower
            return round(sorted_vals[lower] + fraction * (sorted_vals[upper] - sorted_vals[lower]), 4)

        return {
            "p25": _percentile(25),
            "p50": _percentile(50),
            "p75": _percentile(75),
            "p90": _percentile(90),
            "p99": _percentile(99),
        }

    @staticmethod
    def skewness(values: list[float]) -> float:
        """
        Compute the skewness of a distribution.

        Positive skew = right tail is longer (most values are left).
        Negative skew = left tail is longer (most values are right).
        Zero = symmetric.
        """
        n = len(values)
        if n < 3:
            return 0.0

        mean = sum(values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / n)
        if std == 0:
            return 0.0

        return round(
            sum(((v - mean) / std) ** 3 for v in values) / n,
            4,
        )


class CardinalityEstimation:
    """
    Approximate cardinality estimation inspired by HyperLogLog.

    HyperLogLog estimates the number of distinct elements in a
    dataset using much less memory than tracking all unique values.

    HOW HLL WORKS (simplified):
    1. Hash each value.
    2. Count leading zeros in the hash binary representation.
    3. The max number of leading zeros estimates log2(cardinality).

    Real HLL uses multiple "registers" (buckets) for accuracy.
    This simulation provides a simplified version for learning.
    """

    def __init__(self, num_buckets: int = 64) -> None:
        self.num_buckets = num_buckets
        self._registers = [0] * num_buckets

    def add(self, value: Any) -> None:
        """Add a value to the estimator."""
        h = int(hashlib.md5(str(value).encode()).hexdigest(), 16)
        bucket = h % self.num_buckets
        # Count trailing zeros + 1 (approximation of leading zeros)
        remaining = h // self.num_buckets
        rank = 1
        while remaining > 0 and (remaining & 1) == 0:
            rank += 1
            remaining >>= 1
        self._registers[bucket] = max(self._registers[bucket], rank)

    def estimate(self) -> int:
        """Estimate the cardinality (number of distinct values)."""
        m = self.num_buckets
        # Harmonic mean of 2^register values
        indicator = sum(2.0 ** (-r) for r in self._registers)
        alpha = 0.7213 / (1 + 1.079 / m)  # bias correction
        raw_estimate = alpha * m * m / indicator

        # Small range correction
        if raw_estimate <= 2.5 * m:
            zeros = self._registers.count(0)
            if zeros > 0:
                raw_estimate = m * math.log(m / zeros)

        return int(raw_estimate)

    @staticmethod
    def exact_count(values: list[Any]) -> int:
        """Exact distinct count for comparison."""
        return len(set(str(v) for v in values))
