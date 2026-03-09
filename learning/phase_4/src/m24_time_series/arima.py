"""
ARIMA Components -- AutoRegressive and Differencing building blocks.

WHY THIS MATTERS:
ARIMA (AutoRegressive Integrated Moving Average) is the workhorse of
classical time series forecasting. Understanding its components:
  - AR(p): past values predict future values
  - I(d): differencing makes non-stationary data stationary
  - MA(q): past forecast errors predict future values

This module implements AR and Differencing. Together with seasonal
decomposition, these provide the foundation for forecasting ride demand.

For a mobility platform:
  - AR: "demand in the last 3 hours predicts the next hour"
  - Differencing: removes upward trend so we model the changes
"""

import math


class AutoRegressive:
    """AR(p) model -- predicts using p past values.

    y_t = c + phi_1*y_{t-1} + phi_2*y_{t-2} + ... + phi_p*y_{t-p} + epsilon_t

    Fits coefficients using Yule-Walker equations (autocorrelation method).

    WHY AUTOREGRESSIVE:
    Many real-world series have momentum: if demand was high in the last
    hour, it's likely high in the next hour too. AR models capture this
    serial dependence explicitly. The order p controls how far back the
    model looks.

    Yule-Walker:
    Instead of gradient descent, we solve a system of linear equations
    derived from autocorrelation values. This gives the optimal
    coefficients in closed form.
    """

    def __init__(self, order: int = 1):
        if order < 1:
            raise ValueError("Order must be >= 1")
        self.order = order
        self._coefficients: list[float] = []
        self._intercept: float = 0.0
        self._history: list[float] = []

    def fit(self, series: list[float]) -> None:
        """Fit AR(p) model to the series.

        Uses Yule-Walker equations:
          [r(0)   r(1)   ... r(p-1)] [phi_1]   [r(1)]
          [r(1)   r(0)   ... r(p-2)] [phi_2] = [r(2)]
          [  ...                    ] [  ... ]   [ ...]
          [r(p-1) r(p-2) ... r(0)  ] [phi_p]   [r(p)]

        where r(k) is the autocorrelation at lag k.
        """
        if len(series) < self.order + 1:
            raise ValueError(
                f"Series must have at least {self.order + 1} values for AR({self.order})"
            )

        self._history = list(series)

        # Compute autocorrelations for lags 0 through p
        autocorrelations = [
            self._autocorrelation(series, lag) for lag in range(self.order + 1)
        ]

        # Solve Yule-Walker equations
        self._coefficients = self._solve_yule_walker(autocorrelations)

        # Compute intercept: c = mean * (1 - sum(phi_i))
        mean_y = sum(series) / len(series)
        self._intercept = mean_y * (1.0 - sum(self._coefficients))

    def predict(self, steps: int = 1) -> list[float]:
        """Predict future values.

        Uses the last p values from the fitted series (and then its own
        predictions) to forecast forward.
        """
        if not self._coefficients:
            raise RuntimeError("Must call fit() first")

        # Start with the last p values from history
        recent = list(self._history[-self.order :])
        predictions = []

        for _ in range(steps):
            # y_t = c + sum(phi_i * y_{t-i})
            y_t = self._intercept
            for i, phi in enumerate(self._coefficients):
                y_t += phi * recent[-(i + 1)]
            predictions.append(y_t)
            recent.append(y_t)

        return predictions

    def _autocorrelation(self, series: list[float], lag: int) -> float:
        """Compute autocorrelation at a given lag.

        r(k) = cov(y_t, y_{t-k}) / var(y_t)

        Autocorrelation measures how correlated a series is with a
        delayed copy of itself. High r(1) means adjacent values are
        similar; high r(24) for hourly data means same-hour-yesterday
        is similar.
        """
        n = len(series)
        if lag >= n:
            return 0.0

        mean = sum(series) / n
        variance = sum((x - mean) ** 2 for x in series) / n

        if variance == 0:
            return 0.0

        covariance = sum(
            (series[t] - mean) * (series[t - lag] - mean)
            for t in range(lag, n)
        ) / n

        return covariance / variance

    def _solve_yule_walker(self, autocorrelations: list[float]) -> list[float]:
        """Solve Yule-Walker equations to find AR coefficients.

        Builds the Toeplitz matrix of autocorrelations and solves
        the linear system using Gaussian elimination.
        """
        p = self.order
        r = autocorrelations

        # Build Toeplitz matrix R
        R_matrix = [[0.0] * p for _ in range(p)]
        for i in range(p):
            for j in range(p):
                R_matrix[i][j] = r[abs(i - j)]

        # Right-hand side: [r(1), r(2), ..., r(p)]
        rhs = [r[i + 1] for i in range(p)]

        # Gaussian elimination with partial pivoting
        aug = [R_matrix[i][:] + [rhs[i]] for i in range(p)]

        for col in range(p):
            # Partial pivoting
            max_row = col
            max_val = abs(aug[col][col])
            for row in range(col + 1, p):
                if abs(aug[row][col]) > max_val:
                    max_val = abs(aug[row][col])
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            if abs(aug[col][col]) < 1e-12:
                continue

            for row in range(col + 1, p):
                factor = aug[row][col] / aug[col][col]
                for j in range(col, p + 1):
                    aug[row][j] -= factor * aug[col][j]

        # Back substitution
        phi = [0.0] * p
        for i in range(p - 1, -1, -1):
            if abs(aug[i][i]) < 1e-12:
                phi[i] = 0.0
                continue
            phi[i] = aug[i][p]
            for j in range(i + 1, p):
                phi[i] -= aug[i][j] * phi[j]
            phi[i] /= aug[i][i]

        return phi


class Differencing:
    """Makes a time series stationary by differencing.

    d=1: y'_t = y_t - y_{t-1}   (removes linear trend)
    d=2: y''_t = y'_t - y'_{t-1}  (removes quadratic trend)

    WHY DIFFERENCING:
    Most forecasting models assume stationarity (constant mean and
    variance). Real-world data often has trends. Differencing removes
    trends by working with changes instead of levels. The "I" in ARIMA
    stands for "Integrated" -- meaning we difference before fitting AR.

    After forecasting the differenced series, we "undifference" to get
    back to the original scale.
    """

    def __init__(self, d: int = 1):
        if d < 1:
            raise ValueError("Differencing order d must be >= 1")
        self.d = d

    def difference(self, series: list[float]) -> list[float]:
        """Apply d-th order differencing.

        Each round of differencing shortens the series by 1.
        d=1: [a, b, c, d] -> [b-a, c-b, d-c]
        d=2: apply d=1 twice.
        """
        result = list(series)
        for _ in range(self.d):
            if len(result) < 2:
                return []
            result = [result[i] - result[i - 1] for i in range(1, len(result))]
        return result

    def undifference(
        self, differenced: list[float], original_values: list[float]
    ) -> list[float]:
        """Reverse the differencing to recover original scale.

        Needs the original series (or at least its last d values) to
        reconstruct absolute values from differences.

        For d=1: y_t = y'_t + y_{t-1}
        For d=2: first undifference to get d=1 differences, then again.
        """
        result = list(differenced)

        # We need to undifference d times, using the appropriate anchors
        # from the original series
        anchors = list(original_values)

        for step in range(self.d):
            # The anchor is the last value before the differenced portion
            # After first differencing, we lost 1 value; after d, we lost d
            anchor_idx = self.d - step - 1
            if anchor_idx >= len(anchors):
                raise ValueError("Not enough original values to undifference")

            anchor = anchors[anchor_idx]
            reconstructed = [anchor]
            for diff_val in result:
                reconstructed.append(reconstructed[-1] + diff_val)
            result = reconstructed[1:]  # drop the anchor

        return result

    def is_stationary(self, series: list[float], threshold: float = 0.05) -> bool:
        """Simple stationarity check by comparing statistics of halves.

        A truly stationary series should have similar mean and variance
        in its first and second halves.

        This is a simplified heuristic. Production systems use formal
        tests like Augmented Dickey-Fuller (ADF).
        """
        if len(series) < 10:
            return True  # too short to assess

        mid = len(series) // 2
        first_half = series[:mid]
        second_half = series[mid:]

        mean1 = sum(first_half) / len(first_half)
        mean2 = sum(second_half) / len(second_half)

        var1 = sum((x - mean1) ** 2 for x in first_half) / len(first_half)
        var2 = sum((x - mean2) ** 2 for x in second_half) / len(second_half)

        # Check if means and variances are "close"
        overall_mean = sum(series) / len(series)
        overall_var = sum((x - overall_mean) ** 2 for x in series) / len(series)

        if overall_var == 0:
            return True  # constant series is stationary

        mean_diff = abs(mean1 - mean2) / math.sqrt(overall_var + 1e-10)
        var_ratio = max(var1, var2) / (min(var1, var2) + 1e-10)

        return mean_diff < 1.0 and var_ratio < 3.0
