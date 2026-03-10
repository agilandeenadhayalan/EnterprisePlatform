"""
Demand Pattern Detection — Commute, event, weather, and seasonal patterns.

WHY THIS MATTERS:
Different demand patterns require different forecasting strategies:
  - Commute patterns are highly predictable and regular.
  - Event spikes are location-specific and need special handling.
  - Weather effects can be modeled with external data.
  - Seasonal trends affect long-term capacity planning.

Detecting which patterns are present in a cell's demand history helps
the platform choose the right forecasting model and set appropriate
confidence intervals.
"""

from enum import Enum


class PatternType(Enum):
    """Types of demand patterns that can be detected."""
    COMMUTE = "commute"
    EVENT = "event"
    WEATHER = "weather"
    SEASONAL = "seasonal"
    RANDOM = "random"


class DemandPattern:
    """A detected demand pattern with type and strength.

    Strength is a 0-1 score indicating how strong the pattern is.
    Parameters contain pattern-specific details (e.g., peak hours for
    commute, spike magnitude for events).
    """

    def __init__(self, pattern_type: PatternType, strength: float, parameters: dict = None):
        self.pattern_type = pattern_type
        self.strength = min(1.0, max(0.0, strength))
        self.parameters = parameters or {}

    def __repr__(self):
        return f"DemandPattern(type={self.pattern_type.value}, strength={self.strength:.2f})"


class DemandDecomposition:
    """Detect and classify demand patterns from time series data.

    Each detector looks for a specific pattern signature in the hourly
    or daily demand data. The classify() method runs all detectors and
    returns the detected patterns sorted by strength.
    """

    def detect_commute(self, hourly: list[float]) -> DemandPattern | None:
        """Detect commute pattern: morning (7-9) and evening (17-19) peaks.

        A commute pattern exists when both morning and evening hours have
        demand significantly above the daily average. Strength is based
        on how much the peaks exceed the average.

        Args:
            hourly: 24-element list of hourly demand values.

        Returns:
            DemandPattern with COMMUTE type if detected, else None.
        """
        if len(hourly) < 24:
            return None

        mean = sum(hourly) / len(hourly)
        if mean == 0:
            return None

        morning_avg = sum(hourly[7:10]) / 3
        evening_avg = sum(hourly[17:20]) / 3

        morning_ratio = morning_avg / mean
        evening_ratio = evening_avg / mean

        # Both peaks must be at least 1.3x the daily average
        if morning_ratio >= 1.3 and evening_ratio >= 1.3:
            strength = min(1.0, (morning_ratio + evening_ratio - 2.0) / 2.0)
            return DemandPattern(
                PatternType.COMMUTE,
                strength,
                {
                    "morning_peak_ratio": morning_ratio,
                    "evening_peak_ratio": evening_ratio,
                    "morning_peak_hour": 7 + hourly[7:10].index(max(hourly[7:10])),
                    "evening_peak_hour": 17 + hourly[17:20].index(max(hourly[17:20])),
                },
            )
        return None

    def detect_event(
        self, hourly: list[float], baseline: list[float] = None
    ) -> DemandPattern | None:
        """Detect event spike: demand > 2x baseline in any 2-hour window.

        Events cause sudden, localized demand spikes — think concerts,
        sports games, or conferences. We detect them by comparing current
        demand to a baseline (typical day).

        Args:
            hourly: 24-element list of hourly demand values.
            baseline: 24-element list of baseline demand values.

        Returns:
            DemandPattern with EVENT type if detected, else None.
        """
        if baseline is None:
            return None
        if len(hourly) < 24 or len(baseline) < 24:
            return None

        max_ratio = 0.0
        spike_hour = 0

        for h in range(23):
            window_demand = hourly[h] + hourly[h + 1]
            window_baseline = baseline[h] + baseline[h + 1]
            if window_baseline > 0:
                ratio = window_demand / window_baseline
                if ratio > max_ratio:
                    max_ratio = ratio
                    spike_hour = h

        if max_ratio >= 2.0:
            strength = min(1.0, (max_ratio - 1.0) / 3.0)
            return DemandPattern(
                PatternType.EVENT,
                strength,
                {"spike_hour": spike_hour, "spike_ratio": max_ratio},
            )
        return None

    def detect_seasonal(self, daily: list[float]) -> DemandPattern | None:
        """Detect weekly seasonality via correlation with 7-day lag.

        Seasonal patterns mean demand repeats with a fixed period. For
        weekly seasonality, today's demand should correlate with demand
        7 days ago. We compute the Pearson correlation between the series
        and its 7-day lag.

        Args:
            daily: list of daily demand values (at least 14 days).

        Returns:
            DemandPattern with SEASONAL type if detected, else None.
        """
        lag = 7
        if len(daily) < lag * 2:
            return None

        # Compute Pearson correlation between series and its lag
        x = daily[lag:]
        y = daily[:-lag]
        n = len(x)

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5

        if std_x == 0 or std_y == 0:
            return None

        correlation = cov / (std_x * std_y)

        if correlation >= 0.5:
            return DemandPattern(
                PatternType.SEASONAL,
                min(1.0, correlation),
                {"lag_correlation": correlation, "period_days": lag},
            )
        return None

    def classify(
        self, hourly: list[float], baseline: list[float] = None
    ) -> list[DemandPattern]:
        """Run all detectors and return detected patterns sorted by strength.

        Args:
            hourly: 24-element list of hourly demand values.
            baseline: optional 24-element baseline for event detection.

        Returns:
            List of DemandPattern objects sorted by strength (descending).
        """
        patterns = []

        commute = self.detect_commute(hourly)
        if commute:
            patterns.append(commute)

        event = self.detect_event(hourly, baseline)
        if event:
            patterns.append(event)

        # For seasonal detection, we'd need daily data — skip here unless
        # hourly data is long enough to treat as daily
        # classify only handles hourly + event patterns

        patterns.sort(key=lambda p: p.strength, reverse=True)
        return patterns
