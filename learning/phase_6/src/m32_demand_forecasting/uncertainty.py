"""
Prediction Uncertainty — Intervals, quantile regression, and Monte Carlo.

WHY THIS MATTERS:
A point estimate ("ETA is 15 minutes") is less useful than an interval
("ETA is 12-18 minutes with 90% confidence"). Uncertainty quantification
lets platforms set appropriate buffers, trigger surge pricing only when
needed, and communicate reliability to users.

Key concepts:
  - PredictionInterval: a lower-upper bound with a confidence level.
  - QuantileRegression: compute prediction intervals from historical data
    using percentiles.
  - MonteCarloDropout: simulate model uncertainty by adding noise to a
    base prediction and computing statistics over the samples.
  - Calibration: do the stated confidence levels match reality?
"""

import math
import random


class PredictionInterval:
    """A prediction interval with lower bound, upper bound, and confidence.

    The confidence level (e.g., 0.90) means we expect 90% of actual
    values to fall within [lower, upper]. Width = upper - lower.
    """

    def __init__(self, lower: float, upper: float, confidence_level: float):
        if lower > upper:
            raise ValueError(f"lower ({lower}) must be <= upper ({upper})")
        if not 0 < confidence_level <= 1:
            raise ValueError(f"confidence_level must be in (0, 1], got {confidence_level}")
        self.lower = lower
        self.upper = upper
        self.confidence_level = confidence_level

    def width(self) -> float:
        """Width of the interval."""
        return self.upper - self.lower

    def contains(self, value: float) -> bool:
        """Check if a value falls within the interval."""
        return self.lower <= value <= self.upper

    def __repr__(self):
        return (
            f"PredictionInterval(lower={self.lower:.2f}, upper={self.upper:.2f}, "
            f"confidence={self.confidence_level:.0%})"
        )


class QuantileRegression:
    """Simplified quantile regression using percentile method.

    Given a collection of observed values, prediction intervals are
    computed by taking the appropriate percentiles. For example, a 90%
    interval uses the 5th and 95th percentiles.

    This is the non-parametric approach — no distributional assumptions.
    """

    def __init__(self):
        self._values: list[float] = []

    def fit(self, values: list[float]) -> None:
        """Store and sort the observed values."""
        if not values:
            raise ValueError("Cannot fit with empty data")
        self._values = sorted(values)

    def predict_interval(self, confidence: float) -> PredictionInterval:
        """Compute a prediction interval at the given confidence level.

        Uses the percentile method:
          alpha = 1 - confidence
          lower = values at index floor(alpha/2 * n)
          upper = values at index floor((1 - alpha/2) * n) - 1
        """
        if not self._values:
            raise ValueError("Model not fitted — call fit() first")
        if not 0 < confidence < 1:
            raise ValueError(f"confidence must be in (0, 1), got {confidence}")

        n = len(self._values)
        alpha = 1 - confidence
        lower_idx = int(math.floor(alpha / 2 * n))
        upper_idx = int(math.floor((1 - alpha / 2) * n)) - 1
        lower_idx = max(0, min(lower_idx, n - 1))
        upper_idx = max(0, min(upper_idx, n - 1))

        return PredictionInterval(
            lower=self._values[lower_idx],
            upper=self._values[upper_idx],
            confidence_level=confidence,
        )

    def calibration_error(
        self, intervals: list[PredictionInterval], actuals: list[float]
    ) -> float:
        """Fraction of actual values that fall outside their predicted intervals.

        A well-calibrated model at 90% confidence should have about 10%
        of actuals outside the intervals. If more are outside, the model
        is overconfident; if fewer, it's underconfident.
        """
        if len(intervals) != len(actuals):
            raise ValueError("intervals and actuals must have the same length")
        if not intervals:
            return 0.0

        outside = sum(1 for iv, a in zip(intervals, actuals) if not iv.contains(a))
        return outside / len(intervals)


class MonteCarloDropout:
    """Simulate prediction uncertainty by adding Gaussian noise.

    In real deep learning models, Monte Carlo Dropout runs the model
    multiple times with random dropout masks to get a distribution of
    predictions. Here we simulate this by adding Gaussian noise to a
    base prediction, which captures the same idea: repeated stochastic
    forward passes produce a distribution of outputs.
    """

    def __init__(self, seed: int = None):
        self._rng = random.Random(seed)

    def simulate(
        self, base_prediction: float, noise_std: float, n_samples: int
    ) -> list[float]:
        """Generate n_samples noisy predictions.

        Each sample = base_prediction + Gaussian(0, noise_std).
        """
        if n_samples <= 0:
            raise ValueError(f"n_samples must be positive, got {n_samples}")
        return [base_prediction + self._rng.gauss(0, noise_std) for _ in range(n_samples)]

    def get_interval(
        self, samples: list[float], confidence: float
    ) -> PredictionInterval:
        """Compute a prediction interval from simulated samples.

        Sorts the samples and takes percentile-based bounds.
        """
        if not samples:
            raise ValueError("samples must be non-empty")
        if not 0 < confidence < 1:
            raise ValueError(f"confidence must be in (0, 1), got {confidence}")

        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        alpha = 1 - confidence
        lower_idx = max(0, int(math.floor(alpha / 2 * n)))
        upper_idx = min(n - 1, int(math.floor((1 - alpha / 2) * n)) - 1)
        upper_idx = max(lower_idx, upper_idx)

        return PredictionInterval(
            lower=sorted_samples[lower_idx],
            upper=sorted_samples[upper_idx],
            confidence_level=confidence,
        )
