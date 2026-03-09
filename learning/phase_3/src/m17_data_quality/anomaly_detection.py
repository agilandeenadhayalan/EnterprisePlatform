"""
Statistical Anomaly Detection
================================

Anomaly detection identifies data points that deviate significantly
from expected patterns. This is critical for data quality because
anomalies may indicate:

- Pipeline bugs (wrong data type, missing transformation).
- Source system issues (corrupt data, schema changes).
- Genuine business outliers (fraud, unusual demand).

THREE DETECTION METHODS:

1. **Z-Score** — Flags values more than N standard deviations from the mean.
   Best for normally distributed data.
   Threshold of 3.0 catches ~0.3% of values in a normal distribution.

2. **IQR (Interquartile Range)** — Flags values below Q1 - 1.5*IQR
   or above Q3 + 1.5*IQR. Robust to skewed distributions.
   Does not assume normality.

3. **Moving Average** — Flags values that deviate from the rolling mean
   by more than a threshold. Good for time-series data where the
   baseline shifts over time.

Each method has trade-offs:
- Z-Score: Simple, fast, but assumes normality. Affected by outliers.
- IQR: Robust, no distribution assumption, but static threshold.
- Moving Average: Adapts to trends, but needs a window size tuning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Anomaly:
    """A detected anomaly."""
    index: int
    value: float
    expected: float
    deviation: float
    severity: str  # "low", "medium", "high"
    method: str


@dataclass
class AnomalyReport:
    """Summary of anomaly detection results."""
    method: str
    total_points: int
    anomaly_count: int
    anomaly_rate: float
    anomalies: list[Anomaly]
    threshold_used: float

    @property
    def has_anomalies(self) -> bool:
        return self.anomaly_count > 0


class ZScoreDetector:
    """
    Z-Score anomaly detection.

    Z-score = (value - mean) / std_dev

    Values with |z-score| > threshold are flagged as anomalies.

    Default threshold of 3.0 means values more than 3 standard
    deviations from the mean are anomalies. This is the "three-sigma
    rule" — in a normal distribution, 99.7% of values are within 3 sigma.
    """

    def __init__(self, threshold: float = 3.0) -> None:
        if threshold <= 0:
            raise ValueError("Threshold must be positive")
        self.threshold = threshold

    def detect(self, values: list[float]) -> AnomalyReport:
        """Detect anomalies using z-scores."""
        n = len(values)
        if n < 2:
            return AnomalyReport(
                method="z_score",
                total_points=n,
                anomaly_count=0,
                anomaly_rate=0.0,
                anomalies=[],
                threshold_used=self.threshold,
            )

        mean = sum(values) / n
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / n)

        if std == 0:
            return AnomalyReport(
                method="z_score",
                total_points=n,
                anomaly_count=0,
                anomaly_rate=0.0,
                anomalies=[],
                threshold_used=self.threshold,
            )

        anomalies = []
        for i, v in enumerate(values):
            z = abs(v - mean) / std
            if z > self.threshold:
                severity = "high" if z > self.threshold * 2 else (
                    "medium" if z > self.threshold * 1.5 else "low"
                )
                anomalies.append(Anomaly(
                    index=i,
                    value=v,
                    expected=round(mean, 4),
                    deviation=round(z, 4),
                    severity=severity,
                    method="z_score",
                ))

        return AnomalyReport(
            method="z_score",
            total_points=n,
            anomaly_count=len(anomalies),
            anomaly_rate=round(len(anomalies) / n * 100, 2),
            anomalies=anomalies,
            threshold_used=self.threshold,
        )


class IQRDetector:
    """
    IQR-based anomaly detection.

    IQR = Q3 - Q1 (interquartile range).
    Lower fence = Q1 - multiplier * IQR.
    Upper fence = Q3 + multiplier * IQR.

    Values outside the fences are anomalies.

    Default multiplier of 1.5 is the standard for mild outliers.
    3.0 is used for extreme outliers.

    Advantages over Z-Score:
    - Does not assume normal distribution.
    - Robust to extreme outliers (they don't affect Q1/Q3 much).
    """

    def __init__(self, multiplier: float = 1.5) -> None:
        if multiplier <= 0:
            raise ValueError("Multiplier must be positive")
        self.multiplier = multiplier

    def detect(self, values: list[float]) -> AnomalyReport:
        """Detect anomalies using IQR fences."""
        n = len(values)
        if n < 4:
            return AnomalyReport(
                method="iqr",
                total_points=n,
                anomaly_count=0,
                anomaly_rate=0.0,
                anomalies=[],
                threshold_used=self.multiplier,
            )

        sorted_vals = sorted(values)
        q1 = self._percentile(sorted_vals, 25)
        q3 = self._percentile(sorted_vals, 75)
        iqr = q3 - q1

        lower_fence = q1 - self.multiplier * iqr
        upper_fence = q3 + self.multiplier * iqr

        anomalies = []
        for i, v in enumerate(values):
            if v < lower_fence or v > upper_fence:
                distance = min(abs(v - lower_fence), abs(v - upper_fence))
                severity = "high" if distance > 2 * iqr else (
                    "medium" if distance > iqr else "low"
                )
                anomalies.append(Anomaly(
                    index=i,
                    value=v,
                    expected=round((q1 + q3) / 2, 4),
                    deviation=round(distance / iqr if iqr > 0 else 0, 4),
                    severity=severity,
                    method="iqr",
                ))

        return AnomalyReport(
            method="iqr",
            total_points=n,
            anomaly_count=len(anomalies),
            anomaly_rate=round(len(anomalies) / n * 100, 2),
            anomalies=anomalies,
            threshold_used=self.multiplier,
        )

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        """Compute the p-th percentile."""
        n = len(sorted_values)
        idx = (p / 100) * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        fraction = idx - lower
        return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


class MovingAverageDetector:
    """
    Moving average anomaly detection for time-series data.

    Computes a rolling average over a window of past values.
    If a new value deviates from the rolling average by more
    than threshold * rolling_std_dev, it's flagged as an anomaly.

    This adapts to trends: if the average fare gradually increases
    from $20 to $30 over a month, that's normal. But a sudden
    spike to $100 is anomalous.
    """

    def __init__(self, window_size: int = 5, threshold: float = 2.0) -> None:
        if window_size < 2:
            raise ValueError("Window size must be at least 2")
        if threshold <= 0:
            raise ValueError("Threshold must be positive")
        self.window_size = window_size
        self.threshold = threshold

    def detect(self, values: list[float]) -> AnomalyReport:
        """Detect anomalies using moving average deviation."""
        n = len(values)
        anomalies = []

        for i in range(self.window_size, n):
            window = values[i - self.window_size:i]
            mean = sum(window) / len(window)
            std = math.sqrt(sum((v - mean) ** 2 for v in window) / len(window))

            if std == 0:
                # When all window values are identical, any different value
                # is a clear anomaly — infinite deviation from a flat line.
                if values[i] != mean:
                    anomalies.append(Anomaly(
                        index=i,
                        value=values[i],
                        expected=round(mean, 4),
                        deviation=float("inf"),
                        severity="high",
                        method="moving_average",
                    ))
                continue

            deviation = abs(values[i] - mean) / std
            if deviation > self.threshold:
                severity = "high" if deviation > self.threshold * 2 else (
                    "medium" if deviation > self.threshold * 1.5 else "low"
                )
                anomalies.append(Anomaly(
                    index=i,
                    value=values[i],
                    expected=round(mean, 4),
                    deviation=round(deviation, 4),
                    severity=severity,
                    method="moving_average",
                ))

        return AnomalyReport(
            method="moving_average",
            total_points=n,
            anomaly_count=len(anomalies),
            anomaly_rate=round(len(anomalies) / n * 100, 2) if n > 0 else 0.0,
            anomalies=anomalies,
            threshold_used=self.threshold,
        )
