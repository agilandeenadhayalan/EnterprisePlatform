"""
Drift Detection — Statistical methods for detecting distribution shift.

WHY THIS MATTERS:
When a model is deployed, the data it receives in production may differ
from its training data. This "data drift" degrades model performance
silently. By monitoring distribution statistics, we can detect drift
early and trigger retraining before users are affected.

Three complementary methods:
  - PSI: Population Stability Index — binned comparison, industry standard
  - KS Test: Kolmogorov-Smirnov — non-parametric, compares CDFs
  - JS Divergence: Jensen-Shannon — information-theoretic, symmetric
"""

import math


class PSICalculator:
    """Population Stability Index -- measures shift between distributions.

    PSI = sum( (P_i - Q_i) * ln(P_i / Q_i) )

    where P_i = proportion in bin i for the reference distribution
          Q_i = proportion in bin i for the current distribution

    Interpretation:
      < 0.1  : No significant drift
      0.1-0.25: Moderate drift, worth monitoring
      > 0.25 : Significant drift, model likely degraded

    WHY PSI:
    PSI is widely used in financial model monitoring because it gives a
    single number summarizing how much the input distribution has moved.
    It is symmetric-ish (not perfectly symmetric like JSD) and easy to
    threshold for decision-making.
    """

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins
        self._bin_edges: list[float] = []
        self._reference_counts: list[int] = []

    def fit(self, reference: list[float]) -> None:
        """Store reference distribution by computing histogram bins.

        Bins are determined from the reference data and reused when
        computing PSI against current data, so both distributions use
        the same bin boundaries.
        """
        if len(reference) < self.num_bins:
            raise ValueError("Reference data must have at least num_bins elements")

        sorted_ref = sorted(reference)
        n = len(sorted_ref)

        # Create evenly-spaced quantile-based bin edges for robustness
        self._bin_edges = []
        for i in range(self.num_bins + 1):
            idx = int(i * (n - 1) / self.num_bins)
            self._bin_edges.append(sorted_ref[idx])

        # Ensure first/last edges capture everything
        self._bin_edges[0] = float('-inf')
        self._bin_edges[-1] = float('inf')

        self._reference_counts = self._bin_data(reference)

    def compute(self, current: list[float]) -> float:
        """Compute PSI between stored reference and current distribution."""
        if not self._bin_edges:
            raise RuntimeError("Must call fit() with reference data first")
        if len(current) < self.num_bins:
            raise ValueError("Current data must have at least num_bins elements")

        current_counts = self._bin_data(current)

        ref_total = sum(self._reference_counts)
        cur_total = sum(current_counts)

        psi = 0.0
        eps = 1e-6  # avoid log(0)

        for ref_count, cur_count in zip(self._reference_counts, current_counts):
            p = ref_count / ref_total + eps
            q = cur_count / cur_total + eps
            psi += (q - p) * math.log(q / p)

        return psi

    def classify(self, psi_value: float) -> str:
        """Classify drift severity based on PSI value."""
        if psi_value < 0.1:
            return "no_drift"
        elif psi_value < 0.25:
            return "moderate"
        return "significant"

    def _bin_data(self, data: list[float]) -> list[int]:
        """Count data points in each bin."""
        counts = [0] * self.num_bins
        for value in data:
            for i in range(self.num_bins):
                if self._bin_edges[i] <= value < self._bin_edges[i + 1]:
                    counts[i] += 1
                    break
            else:
                # Value equals the upper edge -- put in last bin
                counts[-1] += 1
        return counts


class KSTest:
    """Kolmogorov-Smirnov test -- nonparametric test for distribution equality.

    Compares empirical CDFs of two samples by finding the maximum absolute
    difference between them. The KS statistic D ranges from 0 (identical
    CDFs) to 1 (completely non-overlapping).

    WHY KS TEST:
    Unlike PSI, the KS test does not require binning, making it more
    sensitive to local differences. It is a well-studied statistical test
    with known critical values, enabling formal hypothesis testing.
    """

    def compute(
        self, reference: list[float], current: list[float]
    ) -> tuple[float, float]:
        """Compute KS statistic and approximate p-value.

        Returns:
            (ks_statistic, p_value_approximation)
        """
        if not reference or not current:
            raise ValueError("Both reference and current must be non-empty")

        n1 = len(reference)
        n2 = len(current)

        # Combine and sort all values, tracking which sample they came from
        all_values: list[tuple[float, int]] = []
        for v in reference:
            all_values.append((v, 0))
        for v in current:
            all_values.append((v, 1))
        all_values.sort(key=lambda x: x[0])

        # Walk through sorted values building empirical CDFs
        cdf1 = 0.0
        cdf2 = 0.0
        max_diff = 0.0

        for value, sample_id in all_values:
            if sample_id == 0:
                cdf1 += 1.0 / n1
            else:
                cdf2 += 1.0 / n2
            diff = abs(cdf1 - cdf2)
            if diff > max_diff:
                max_diff = diff

        ks_statistic = max_diff

        # Approximate p-value using the asymptotic formula
        # P(D > d) ~ 2 * exp(-2 * n_eff * d^2)
        # where n_eff = n1*n2 / (n1+n2)
        n_eff = (n1 * n2) / (n1 + n2)
        exponent = -2.0 * n_eff * ks_statistic * ks_statistic
        p_value = 2.0 * math.exp(max(exponent, -500))  # clamp to avoid underflow
        p_value = min(p_value, 1.0)

        return ks_statistic, p_value


class JSDivergence:
    """Jensen-Shannon Divergence -- symmetric version of KL divergence.

    JSD(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
    where M = 0.5 * (P + Q)

    Properties:
      - Symmetric: JSD(P||Q) = JSD(Q||P)
      - Bounded: 0 <= JSD <= ln(2) (using natural log)
      - Zero iff P = Q
      - Square root of JSD is a metric (satisfies triangle inequality)

    WHY JSD:
    KL divergence is asymmetric and can be infinite when one distribution
    has zero probability where the other doesn't. JSD fixes both issues,
    making it a robust and interpretable measure of distribution distance.
    """

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins

    def compute(self, reference: list[float], current: list[float]) -> float:
        """Compute JSD between reference and current distributions."""
        if not reference or not current:
            raise ValueError("Both reference and current must be non-empty")

        # Create bins from combined data for consistent comparison
        combined = reference + current
        min_val = min(combined)
        max_val = max(combined)

        if min_val == max_val:
            return 0.0  # identical constant distributions

        bin_width = (max_val - min_val) / self.num_bins

        # Build probability distributions
        p = self._histogram(reference, min_val, bin_width)
        q = self._histogram(current, min_val, bin_width)

        # M = 0.5 * (P + Q)
        m = [(pi + qi) / 2.0 for pi, qi in zip(p, q)]

        # JSD = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
        return 0.5 * self._kl_divergence(p, m) + 0.5 * self._kl_divergence(q, m)

    def _kl_divergence(self, p: list[float], q: list[float]) -> float:
        """Compute KL(P||Q) = sum(p_i * log(p_i / q_i)).

        Uses small epsilon to avoid log(0) and division by zero.
        """
        eps = 1e-10
        kl = 0.0
        for pi, qi in zip(p, q):
            pi = pi + eps
            qi = qi + eps
            kl += pi * math.log(pi / qi)
        return kl

    def _histogram(self, data: list[float], min_val: float, bin_width: float) -> list[float]:
        """Build normalized histogram (probability distribution)."""
        counts = [0] * self.num_bins
        for value in data:
            idx = int((value - min_val) / bin_width)
            idx = min(idx, self.num_bins - 1)  # clamp last edge
            counts[idx] += 1

        total = sum(counts)
        return [c / total for c in counts]
