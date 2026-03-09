"""
Demand Forecasting -- Predict future ride demand using seasonal patterns.

WHY THIS MATTERS:
Accurate demand forecasting is the cornerstone of mobility platform
operations:
  - Driver allocation: pre-position drivers where demand will surge
  - Pricing: adjust prices based on predicted supply/demand imbalance
  - Capacity planning: ensure enough vehicles are available

This module combines multiple seasonal patterns (hourly, daily) with
trend to produce multi-step forecasts.
"""

import math


class DemandForecaster:
    """Predicts hourly ride demand per zone using seasonal patterns.

    Combines:
      - Hour-of-day effects (rush hour peaks, late-night lulls)
      - Day-of-week effects (weekday vs. weekend patterns)
      - Linear trend (overall growth or decline)

    The model is intentionally simple (no external libraries) to
    demonstrate the core concepts of seasonal forecasting.

    WHY SEASONAL APPROACH:
    Ride demand is highly regular: Monday 8am looks like every other
    Monday 8am. Capturing this regularity with explicit seasonal
    components is both interpretable and effective for short-term
    forecasting (1-48 hours ahead).
    """

    def __init__(self, seasonal_period: int = 24):
        self.seasonal_period = seasonal_period
        self._hourly_pattern: list[float] = []
        self._daily_pattern: list[float] = []
        self._trend_slope: float = 0.0
        self._trend_intercept: float = 0.0
        self._base_mean: float = 0.0
        self._fitted_length: int = 0

    def fit(self, hourly_demand: list[float], hours: list[int] = None) -> None:
        """Fit the forecaster to historical hourly demand data.

        Args:
            hourly_demand: List of demand values (one per hour).
            hours: Optional list of hour-of-day values (0-23).
                   If not provided, assumes sequential starting at 0.
        """
        if len(hourly_demand) < 2 * self.seasonal_period:
            raise ValueError(
                f"Need at least {2 * self.seasonal_period} data points"
            )

        self._fitted_length = len(hourly_demand)
        self._base_mean = sum(hourly_demand) / len(hourly_demand)

        # Extract trend using linear regression
        n = len(hourly_demand)
        xs = list(range(n))
        self._trend_slope, self._trend_intercept = self._linear_regression(
            xs, hourly_demand
        )

        # Detrend the series
        detrended = [
            hourly_demand[i] - (self._trend_slope * i + self._trend_intercept)
            for i in range(n)
        ]

        # Extract hourly pattern (hour-of-day seasonality)
        self._hourly_pattern = self._extract_hourly_pattern(detrended)

        # Extract daily pattern (7-day weekly cycle, if enough data)
        if n >= 7 * self.seasonal_period:
            self._daily_pattern = self._extract_daily_pattern(hourly_demand)
        else:
            self._daily_pattern = [1.0] * 7

    def predict(self, n_hours: int) -> list[float]:
        """Predict demand for the next n_hours.

        Forecast = Trend + Seasonal_hourly + Seasonal_daily_adjustment

        Returns:
            List of predicted demand values.
        """
        if not self._hourly_pattern:
            raise RuntimeError("Must call fit() first")

        predictions = []
        start = self._fitted_length

        for h in range(n_hours):
            t = start + h

            # Trend component
            trend_val = self._trend_slope * t + self._trend_intercept

            # Hourly seasonal component
            hour_pos = t % self.seasonal_period
            seasonal_val = self._hourly_pattern[hour_pos]

            # Daily adjustment
            day_pos = (t // self.seasonal_period) % 7
            daily_factor = self._daily_pattern[day_pos] if self._daily_pattern else 1.0

            # Combine: trend + hourly_season, scaled by daily factor
            forecast = (trend_val + seasonal_val) * daily_factor
            # Demand cannot be negative
            predictions.append(max(0.0, forecast))

        return predictions

    def _extract_hourly_pattern(self, demand: list[float]) -> list[float]:
        """Extract hour-of-day seasonal pattern.

        Averages demand values at each hour position across all complete
        days. The result represents the typical hourly shape.
        """
        pattern = [0.0] * self.seasonal_period
        counts = [0] * self.seasonal_period

        for i, val in enumerate(demand):
            pos = i % self.seasonal_period
            pattern[pos] += val
            counts[pos] += 1

        for pos in range(self.seasonal_period):
            if counts[pos] > 0:
                pattern[pos] /= counts[pos]

        return pattern

    def _extract_daily_pattern(self, demand: list[float]) -> list[float]:
        """Extract day-of-week pattern as multiplicative factors.

        Computes average demand for each day of the week, then normalizes
        by overall daily average to get factors (1.0 = average day).
        """
        daily_totals: dict[int, list[float]] = {d: [] for d in range(7)}
        hours_per_day = self.seasonal_period

        n_complete_days = len(demand) // hours_per_day
        for day in range(n_complete_days):
            start = day * hours_per_day
            end = start + hours_per_day
            day_total = sum(demand[start:end])
            day_of_week = day % 7
            daily_totals[day_of_week].append(day_total)

        pattern = []
        for d in range(7):
            if daily_totals[d]:
                pattern.append(sum(daily_totals[d]) / len(daily_totals[d]))
            else:
                pattern.append(1.0)

        # Normalize to average 1.0
        avg = sum(pattern) / len(pattern)
        if avg > 0:
            pattern = [p / avg for p in pattern]

        return pattern

    def _linear_regression(
        self, x: list[float], y: list[float]
    ) -> tuple[float, float]:
        """Simple linear regression: y = slope * x + intercept."""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)

        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-12:
            return 0.0, sum_y / n if n > 0 else 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        return slope, intercept
