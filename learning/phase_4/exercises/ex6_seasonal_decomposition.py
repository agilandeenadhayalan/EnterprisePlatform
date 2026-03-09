"""
Exercise 6: Seasonal Decomposition
========================================
Additive decomposition separates a time series into:
    Y = Trend + Seasonal + Residual

Steps:
1. Trend: Centered moving average smooths out seasonality
2. Seasonal: Average (Y - Trend) at each position in the cycle
3. Residual: Y - Trend - Seasonal

WHY DECOMPOSITION:
Understanding WHAT drives a time series is essential before forecasting.
Is demand growing? Is there a weekly pattern? Are there unexplained
spikes? Decomposition answers these questions and makes each component
independently analyzable and forecastable.

YOUR TASK:
1. Implement extract_trend() — centered moving average
2. Implement extract_seasonal() — average detrended values by position
3. Implement decompose() — combine trend, seasonal, residual
"""


class SeasonalDecomposer:
    """Additive time series decomposition: Y = Trend + Seasonal + Residual."""

    def __init__(self, period: int):
        self.period = period

    def extract_trend(self, series: list[float]) -> list[float | None]:
        """Extract trend using centered moving average.

        For a window of size `period`:
        - If period is ODD: trend[i] = mean(series[i-h : i+h+1])
          where h = period // 2
        - If period is EVEN: first compute window-sized MA, then
          average adjacent values to center it.

        Edge values where the window doesn't fit should be None.

        Args:
            series: The time series values.

        Returns:
            List of same length as series. Interior values are the
            moving average; edges are None.
        """
        # TODO: Implement (~10 lines)
        # Hint: For odd period, iterate from h to len-h
        # Hint: For even period, do a two-step process
        raise NotImplementedError("Implement centered moving average")

    def extract_seasonal(self, series: list[float],
                         trend: list[float | None]) -> list[float]:
        """Extract seasonal component from detrended series.

        Steps:
        1. Compute detrended values: series[i] - trend[i] (where trend is not None)
        2. Average detrended values at each seasonal position (i % period)
        3. Center the seasonal pattern so it sums to approximately 0

        Args:
            series: Original time series.
            trend: Trend component (may contain None at edges).

        Returns:
            Seasonal component, same length as series. Repeats every period.
        """
        # TODO: Implement (~10 lines)
        # Hint: Build a list of averages, one per position 0..period-1
        # Hint: Subtract the overall mean of those averages to center them
        # Hint: Tile the pattern across the full series length
        raise NotImplementedError("Implement seasonal extraction")

    def decompose(self, series: list[float]) -> dict:
        """Full additive decomposition: Y = Trend + Seasonal + Residual.

        Returns:
            {"trend": [...], "seasonal": [...], "residual": [...]}
            Residual[i] = series[i] - trend[i] - seasonal[i]
            (None where trend is None)
        """
        # TODO: Implement (~5 lines)
        # Hint: Call extract_trend, then extract_seasonal
        # Hint: Compute residual = series - trend - seasonal
        raise NotImplementedError("Implement full decomposition")


# ── Verification ──

def _verify():
    """Run basic checks to verify your implementation."""
    # Generate simple seasonal data: trend + repeating pattern
    period = 4
    n = 40
    trend_vals = [10 + 0.5 * i for i in range(n)]
    seasonal_pattern = [3, -1, -3, 1]  # sums to 0
    data = [
        trend_vals[i] + seasonal_pattern[i % period]
        for i in range(n)
    ]

    decomp = SeasonalDecomposer(period=period)

    # Test 1: Trend extraction
    trend = decomp.extract_trend(data)
    assert len(trend) == n
    non_none = [v for v in trend if v is not None]
    assert len(non_none) > n // 2, "Too many None values in trend"
    # Trend should be increasing
    assert non_none[-1] > non_none[0], "Trend should be increasing for this data"
    print(f"[PASS] Trend extracted ({len(non_none)} non-None values)")

    # Test 2: Seasonal extraction
    seasonal = decomp.extract_seasonal(data, trend)
    assert len(seasonal) == n
    # Seasonal should repeat
    for i in range(period, n):
        assert abs(seasonal[i] - seasonal[i % period]) < 0.001, \
            f"Seasonal not repeating at index {i}"
    print(f"[PASS] Seasonal repeats correctly: {seasonal[:period]}")

    # Test 3: Full decomposition and reconstruction
    result = decomp.decompose(data)
    for i in range(n):
        if result["trend"][i] is not None:
            reconstructed = (
                result["trend"][i] + result["seasonal"][i] + result["residual"][i]
            )
            assert abs(reconstructed - data[i]) < 0.01, \
                f"Reconstruction failed at index {i}: {reconstructed} != {data[i]}"
    print("[PASS] Trend + Seasonal + Residual reconstructs original series")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
