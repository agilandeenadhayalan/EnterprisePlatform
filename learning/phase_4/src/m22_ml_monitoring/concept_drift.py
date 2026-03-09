"""
Concept Drift Detection -- Detects when the learned relationship changes.

WHY THIS MATTERS:
Data drift (input distribution shift) can be detected by monitoring features.
But *concept drift* is subtler: the inputs may look the same, yet the
correct output has changed. For example, "what makes a ride high-demand"
may shift due to a new competitor entering the market.

Concept drift detection monitors model errors over time, looking for
sustained increases that indicate the model's learned mapping is stale.

Three approaches:
  - Simple sliding window error monitoring
  - Page-Hinkley test: sequential change-point detection
  - ADWIN: adaptive windowing with statistical change detection
"""

import math


class ConceptDriftDetector:
    """Detects when the relationship between features and target changes.

    Unlike data drift (input distribution shift), concept drift means
    the mapping f(x) -> y has changed even if x's distribution is stable.

    Strategy: Monitor prediction errors in a sliding window. If the error
    distribution shifts upward, the model's learned concept is stale.

    WHY SLIDING WINDOW:
    A sliding window focuses on recent errors, making the detector
    responsive to gradual drift while ignoring ancient history.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._errors: list[float] = []

    def add_error(self, error: float) -> None:
        """Add a prediction error observation."""
        self._errors.append(error)

    def detect(self) -> dict:
        """Analyze error window for concept drift signals.

        Returns:
            dict with keys:
              - is_drifted: bool
              - error_mean: float (mean of recent errors)
              - error_trend: float (slope of error over window)
              - method: str ("sliding_window")
        """
        if len(self._errors) < self.window_size:
            return {
                "is_drifted": False,
                "error_mean": _mean(self._errors) if self._errors else 0.0,
                "error_trend": 0.0,
                "method": "sliding_window",
            }

        window = self._errors[-self.window_size :]
        first_half = window[: self.window_size // 2]
        second_half = window[self.window_size // 2 :]

        mean_first = _mean(first_half)
        mean_second = _mean(second_half)

        # Trend: positive means errors are increasing
        error_trend = mean_second - mean_first

        # Standard deviation of first half for threshold
        std_first = _std(first_half)

        # Drift if second half mean exceeds first half by > 2 std deviations
        is_drifted = error_trend > max(2.0 * std_first, 0.01)

        return {
            "is_drifted": is_drifted,
            "error_mean": _mean(window),
            "error_trend": error_trend,
            "method": "sliding_window",
        }


class PageHinkleyDetector:
    """Page-Hinkley test -- sequential analysis for change point detection.

    Accumulates deviations from the running mean. When the cumulative
    deviation exceeds a threshold, a change (drift) is signaled.

    WHY PAGE-HINKLEY:
    Unlike batch methods that need a full window, Page-Hinkley processes
    one observation at a time, making it suitable for streaming scenarios.
    The alpha parameter controls sensitivity to small changes vs. noise.

    Algorithm:
      m_t = (1/t) * sum(x_1 ... x_t)           (running mean)
      U_t = U_{t-1} + (x_t - m_t - alpha)       (cumulative sum)
      M_t = max(U_1 ... U_t)                     (maximum cumulative sum)
      Drift detected if M_t - U_t > threshold
    """

    def __init__(self, threshold: float = 50.0, alpha: float = 0.005):
        self.threshold = threshold
        self.alpha = alpha
        self._n = 0
        self._sum = 0.0
        self._cumulative = 0.0
        self._min_cumulative = float("inf")

    def update(self, value: float) -> bool:
        """Process a new observation. Returns True if drift detected."""
        self._n += 1
        self._sum += value
        running_mean = self._sum / self._n

        # Accumulate deviation from mean, biased by alpha
        self._cumulative += value - running_mean - self.alpha

        if self._cumulative < self._min_cumulative:
            self._min_cumulative = self._cumulative

        # Check if cumulative deviation has grown beyond threshold
        return (self._cumulative - self._min_cumulative) > self.threshold

    def reset(self) -> None:
        """Reset detector state."""
        self._n = 0
        self._sum = 0.0
        self._cumulative = 0.0
        self._min_cumulative = float("inf")


class ADWINDetector:
    """Simplified ADWIN (ADaptive WINdowing) -- detects distribution changes
    by comparing means of sub-windows.

    ADWIN maintains a window of recent observations. At each step, it checks
    whether any split of the window into two consecutive sub-windows yields
    significantly different means. If so, the older portion is dropped.

    WHY ADWIN:
    ADWIN automatically adjusts its window size: large windows when data
    is stable (for better statistics) and small windows after a change
    (for faster adaptation). This makes it self-tuning.

    Simplified version: only checks the midpoint split rather than all
    possible splits, trading some detection power for efficiency.
    """

    def __init__(self, delta: float = 0.002):
        self.delta = delta
        self._window: list[float] = []

    def update(self, value: float) -> bool:
        """Add observation and check for change. Returns True if change detected."""
        self._window.append(value)

        if len(self._window) < 10:
            return False

        if self._has_change():
            # Drop older half of the window
            mid = len(self._window) // 2
            self._window = self._window[mid:]
            return True

        return False

    def _has_change(self) -> bool:
        """Check if window contains a distributional change at midpoint.

        Uses Hoeffding bound: two sub-window means differ significantly if
        |mean1 - mean2| > epsilon, where epsilon depends on sub-window
        sizes and the confidence parameter delta.
        """
        n = len(self._window)
        if n < 6:
            return False

        mid = n // 2
        w1 = self._window[:mid]
        w2 = self._window[mid:]

        n1 = len(w1)
        n2 = len(w2)
        mean1 = _mean(w1)
        mean2 = _mean(w2)

        # Hoeffding bound for the difference of means
        # epsilon = sqrt((1/(2*n)) * ln(4/delta))
        # We use harmonic mean of sizes for combined bound
        m = 1.0 / (1.0 / n1 + 1.0 / n2)
        epsilon = math.sqrt(math.log(4.0 / self.delta) / (2.0 * m))

        return abs(mean1 - mean2) > epsilon


# ── Helper functions ──

def _mean(values: list[float]) -> float:
    """Compute arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    """Compute population standard deviation."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)
