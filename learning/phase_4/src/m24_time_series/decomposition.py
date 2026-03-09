"""
Time Series Decomposition -- Separating signal from noise.

WHY THIS MATTERS:
Raw time series data is a mix of long-term trend, repeating seasonal
patterns, and irregular noise. Decomposition separates these components
so each can be analyzed and forecast independently.

For a mobility platform:
  - Trend: overall growth in ride demand year-over-year
  - Seasonal: rush hour patterns, weekend dips, holiday spikes
  - Residual: unpredictable events (weather, accidents, concerts)

Two models:
  - Additive: Y = T + S + R  (components add up)
    Use when seasonal variation is constant regardless of level.
  - Multiplicative: Y = T * S * R  (components multiply)
    Use when seasonal variation grows with the level.
"""


class AdditiveDecomposition:
    """Decomposes time series: Y = Trend + Seasonal + Residual.

    Steps:
    1. Trend: centered moving average smooths out seasonality
    2. Seasonal: average of (Y - Trend) at each seasonal position
    3. Residual: Y - Trend - Seasonal (what's left unexplained)

    WHY ADDITIVE:
    Appropriate when seasonal fluctuations are roughly constant in
    absolute terms. E.g., demand always increases by ~100 rides during
    rush hour, regardless of the baseline demand level.
    """

    def __init__(self, period: int):
        if period < 2:
            raise ValueError("Period must be >= 2")
        self.period = period

    def decompose(self, series: list[float]) -> dict:
        """Decompose series into trend, seasonal, and residual components.

        Args:
            series: Time series values (length must be >= 2 * period).

        Returns:
            {"trend": [...], "seasonal": [...], "residual": [...]}
            Trend and residual will have None at edges where moving average
            cannot be computed.
        """
        if len(series) < 2 * self.period:
            raise ValueError(
                f"Series length ({len(series)}) must be >= 2*period ({2 * self.period})"
            )

        # Step 1: Extract trend via centered moving average
        trend = self._moving_average(series, self.period)

        # Step 2: Detrend and compute seasonal component
        detrended = [None] * len(series)
        for i in range(len(series)):
            if trend[i] is not None:
                detrended[i] = series[i] - trend[i]

        # Average detrended values by position in seasonal cycle
        seasonal_avgs = [0.0] * self.period
        seasonal_counts = [0] * self.period
        for i in range(len(series)):
            if detrended[i] is not None:
                pos = i % self.period
                seasonal_avgs[pos] += detrended[i]
                seasonal_counts[pos] += 1

        for pos in range(self.period):
            if seasonal_counts[pos] > 0:
                seasonal_avgs[pos] /= seasonal_counts[pos]

        # Center the seasonal component (subtract mean so it sums to ~0)
        seasonal_mean = sum(seasonal_avgs) / self.period
        seasonal_avgs = [s - seasonal_mean for s in seasonal_avgs]

        # Extend seasonal pattern across full series
        seasonal = [seasonal_avgs[i % self.period] for i in range(len(series))]

        # Step 3: Residual = Y - Trend - Seasonal
        residual = [None] * len(series)
        for i in range(len(series)):
            if trend[i] is not None:
                residual[i] = series[i] - trend[i] - seasonal[i]

        return {
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual,
        }

    def _moving_average(self, series: list[float], window: int) -> list[float | None]:
        """Compute centered moving average.

        For even windows (common for seasonal decomposition), uses a
        2-step process: first a window-sized MA, then a 2-point MA to
        center it. This ensures the smoothed value is aligned with the
        original time points.
        """
        n = len(series)
        result = [None] * n

        half = window // 2

        if window % 2 == 1:
            # Odd window: simple centered average
            for i in range(half, n - half):
                total = sum(series[i - half : i + half + 1])
                result[i] = total / window
        else:
            # Even window: first pass then center with 2-point average
            first_pass = [None] * n
            for i in range(half, n - half + 1):
                if i - half >= 0 and i + half <= n:
                    total = sum(series[i - half : i + half])
                    first_pass[i] = total / window

            for i in range(1, n):
                if first_pass[i - 1] is not None and first_pass[i] is not None:
                    result[i] = (first_pass[i - 1] + first_pass[i]) / 2.0

        return result


class MultiplicativeDecomposition:
    """Decomposes time series: Y = Trend * Seasonal * Residual.

    Same algorithm as additive, but uses division instead of subtraction:
      Seasonal: Y / Trend (averaged by position)
      Residual: Y / (Trend * Seasonal)

    WHY MULTIPLICATIVE:
    Appropriate when seasonal variation grows proportionally with the
    level. E.g., rush-hour demand doubles regardless of whether baseline
    is 100 or 1000 rides.
    """

    def __init__(self, period: int):
        if period < 2:
            raise ValueError("Period must be >= 2")
        self.period = period
        self._additive = AdditiveDecomposition(period)

    def decompose(self, series: list[float]) -> dict:
        """Decompose series multiplicatively.

        Returns:
            {"trend": [...], "seasonal": [...], "residual": [...]}
            Seasonal values are ratios (1.0 = no seasonal effect).
        """
        if len(series) < 2 * self.period:
            raise ValueError(
                f"Series length ({len(series)}) must be >= 2*period ({2 * self.period})"
            )

        # Step 1: Trend (same as additive)
        trend = self._additive._moving_average(series, self.period)

        # Step 2: Detrend by division
        detrended = [None] * len(series)
        for i in range(len(series)):
            if trend[i] is not None and trend[i] != 0:
                detrended[i] = series[i] / trend[i]

        # Average detrended ratios by seasonal position
        seasonal_avgs = [0.0] * self.period
        seasonal_counts = [0] * self.period
        for i in range(len(series)):
            if detrended[i] is not None:
                pos = i % self.period
                seasonal_avgs[pos] += detrended[i]
                seasonal_counts[pos] += 1

        for pos in range(self.period):
            if seasonal_counts[pos] > 0:
                seasonal_avgs[pos] /= seasonal_counts[pos]

        # Normalize so seasonal factors average to 1.0
        seasonal_mean = sum(seasonal_avgs) / self.period
        if seasonal_mean != 0:
            seasonal_avgs = [s / seasonal_mean for s in seasonal_avgs]

        # Extend seasonal pattern
        seasonal = [seasonal_avgs[i % self.period] for i in range(len(series))]

        # Step 3: Residual = Y / (Trend * Seasonal)
        residual = [None] * len(series)
        for i in range(len(series)):
            if trend[i] is not None and seasonal[i] != 0 and trend[i] != 0:
                residual[i] = series[i] / (trend[i] * seasonal[i])

        return {
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual,
        }
