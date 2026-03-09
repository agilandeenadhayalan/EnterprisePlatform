"""
Uncertainty Quantification -- Prediction intervals for time series forecasts.

WHY THIS MATTERS:
A point forecast ("demand will be 150 rides") is incomplete. Decision-makers
need prediction intervals ("demand will be 120-180 rides with 95% confidence")
to plan for worst-case and best-case scenarios.

For a mobility platform:
  - Upper bound: ensure enough drivers are available (avoid unfulfilled rides)
  - Lower bound: don't over-allocate drivers (avoid idle fleet costs)
  - Interval width: wider intervals = more uncertainty = riskier decisions

Two approaches:
  - Bootstrap: model-free, uses resampled residuals
  - Conformal prediction: calibration-based, provides coverage guarantees
"""

import math
import random


class BootstrapInterval:
    """Prediction intervals using bootstrap resampling.

    Creates many bootstrap samples of residuals, adds them to the point
    forecast, and uses the distribution of bootstrapped predictions to
    construct confidence intervals.

    WHY BOOTSTRAP:
    Bootstrap makes no assumptions about the error distribution. If
    residuals are skewed (e.g., demand spikes are larger than dips),
    bootstrap intervals will naturally be asymmetric, unlike Gaussian
    intervals that are always symmetric.

    Algorithm:
    1. Resample residuals with replacement (n_bootstrap times)
    2. Add resampled residuals to point forecast
    3. Take alpha/2 and 1-alpha/2 quantiles as interval bounds
    """

    def __init__(
        self, n_bootstrap: int = 100, confidence: float = 0.95, seed: int = 42
    ):
        if not 0 < confidence < 1:
            raise ValueError("Confidence must be between 0 and 1")
        self.n_bootstrap = n_bootstrap
        self.confidence = confidence
        self.seed = seed

    def compute(
        self, residuals: list[float], point_forecast: list[float]
    ) -> dict:
        """Compute bootstrap prediction intervals.

        Args:
            residuals: Historical forecast errors (actual - predicted).
            point_forecast: Point predictions for future time steps.

        Returns:
            {"lower": [...], "upper": [...], "point": [...]}
        """
        if not residuals:
            raise ValueError("Residuals list must be non-empty")

        rng = random.Random(self.seed)
        n_steps = len(point_forecast)
        alpha = 1.0 - self.confidence

        # For each forecast step, collect bootstrap predictions
        lower = []
        upper = []

        for step in range(n_steps):
            # Generate bootstrap predictions by adding resampled residuals
            bootstrap_preds = []
            for _ in range(self.n_bootstrap):
                sampled_residual = rng.choice(residuals)
                bootstrap_preds.append(point_forecast[step] + sampled_residual)

            bootstrap_preds.sort()

            # Extract quantiles
            lower_idx = int(alpha / 2 * self.n_bootstrap)
            upper_idx = int((1 - alpha / 2) * self.n_bootstrap) - 1
            lower_idx = max(0, min(lower_idx, len(bootstrap_preds) - 1))
            upper_idx = max(0, min(upper_idx, len(bootstrap_preds) - 1))

            lower.append(bootstrap_preds[lower_idx])
            upper.append(bootstrap_preds[upper_idx])

        return {
            "lower": lower,
            "upper": upper,
            "point": list(point_forecast),
        }


class ConformalPredictor:
    """Basic conformal prediction -- calibration-based prediction intervals.

    Uses calibration set residuals to determine interval width that
    achieves desired coverage probability.

    WHY CONFORMAL PREDICTION:
    Unlike bootstrap, conformal prediction provides a theoretical
    coverage guarantee: the prediction interval will contain the true
    value at least (1-alpha)% of the time, regardless of the underlying
    distribution, as long as data is exchangeable.

    Algorithm:
    1. Compute absolute residuals on a calibration set
    2. Find the (1-alpha) quantile of absolute residuals
    3. Prediction interval = point_forecast +/- quantile

    This gives symmetric intervals. The width adapts to the model's
    actual error magnitude on calibration data.
    """

    def __init__(self, confidence: float = 0.90):
        if not 0 < confidence < 1:
            raise ValueError("Confidence must be between 0 and 1")
        self.confidence = confidence
        self._quantile: float = 0.0
        self._calibrated = False

    def calibrate(self, calibration_residuals: list[float]) -> None:
        """Calibrate using residuals from a held-out calibration set.

        Computes the quantile of absolute residuals that determines
        the interval half-width.
        """
        if not calibration_residuals:
            raise ValueError("Calibration residuals must be non-empty")

        abs_residuals = sorted(abs(r) for r in calibration_residuals)
        n = len(abs_residuals)

        # Find the ceil((n+1) * confidence) / n quantile
        # This is the conformal quantile that guarantees coverage
        quantile_idx = int(math.ceil((n + 1) * self.confidence)) - 1
        quantile_idx = max(0, min(quantile_idx, n - 1))

        self._quantile = abs_residuals[quantile_idx]
        self._calibrated = True

    def predict_interval(self, point_forecast: float) -> tuple[float, float]:
        """Compute prediction interval for a single point forecast.

        Returns:
            (lower_bound, upper_bound)
        """
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() first")

        return (
            point_forecast - self._quantile,
            point_forecast + self._quantile,
        )
