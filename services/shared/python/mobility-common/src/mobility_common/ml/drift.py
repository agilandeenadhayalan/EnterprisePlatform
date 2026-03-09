"""
Data drift detection utilities for monitoring model input distributions.

Provides pure-Python implementations of common statistical tests used
to detect distribution drift between a reference (training) dataset and
a current (serving) dataset:

  - **PSI** (Population Stability Index):  Measures overall distribution
    shift.  Values > 0.25 typically indicate significant drift.
  - **KS test** (Kolmogorov-Smirnov):  Non-parametric test comparing
    two empirical CDFs.  P-values < 0.05 suggest distributions differ.
  - **JSD** (Jensen-Shannon Divergence):  Symmetric, bounded version of
    KL divergence.  Values > 0.1 suggest meaningful drift.

All implementations use only the ``math`` standard-library module so
there is no dependency on scipy or numpy in the shared library.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default thresholds for common drift detection methods
_DEFAULT_THRESHOLDS: Dict[str, float] = {
    "psi": 0.25,
    "ks": 0.05,     # p-value threshold (drift if p < threshold)
    "jsd": 0.1,
}


class DriftDetector:
    """Static-method collection for distribution drift detection.

    All methods are pure Python and operate on lists of numeric values.
    No external dependencies (scipy, numpy) are required.

    Examples
    --------
    >>> ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    >>> cur = [2.0, 3.0, 4.0, 5.0, 6.0]
    >>> DriftDetector.psi(ref, cur)
    0.03...
    >>> DriftDetector.is_drifted(0.3, "psi")
    True
    """

    @staticmethod
    def psi(
        reference: List[float],
        current: List[float],
        num_bins: int = 10,
    ) -> float:
        """Calculate the Population Stability Index.

        PSI quantifies how much the distribution of *current* has shifted
        relative to *reference*.

        Parameters
        ----------
        reference : list[float]
            Values from the reference (training) distribution.
        current : list[float]
            Values from the current (serving) distribution.
        num_bins : int
            Number of equal-width bins (default 10).

        Returns
        -------
        float
            PSI value.  0 means no shift; > 0.25 is typically significant.

        Raises
        ------
        ValueError
            If either list is empty.
        """
        if not reference or not current:
            raise ValueError("Both reference and current must be non-empty")

        # Determine bin edges from the reference distribution
        all_vals = reference + current
        min_val = min(all_vals)
        max_val = max(all_vals)

        if min_val == max_val:
            return 0.0

        bin_width = (max_val - min_val) / num_bins
        edges = [min_val + i * bin_width for i in range(num_bins + 1)]
        edges[-1] = max_val + 1e-10  # Include the max value

        ref_counts = DriftDetector._bin_counts(reference, edges)
        cur_counts = DriftDetector._bin_counts(current, edges)

        # Convert to proportions with smoothing to avoid log(0)
        epsilon = 1e-10
        ref_total = len(reference)
        cur_total = len(current)

        psi_value = 0.0
        for i in range(num_bins):
            ref_pct = (ref_counts[i] / ref_total) + epsilon
            cur_pct = (cur_counts[i] / cur_total) + epsilon
            psi_value += (cur_pct - ref_pct) * math.log(cur_pct / ref_pct)

        logger.debug("PSI = %.6f (bins=%d)", psi_value, num_bins)
        return psi_value

    @staticmethod
    def ks_test(
        reference: List[float],
        current: List[float],
    ) -> Tuple[float, float]:
        """Perform a two-sample Kolmogorov-Smirnov test.

        Compares the empirical CDFs of *reference* and *current* to assess
        whether they are drawn from the same distribution.

        Parameters
        ----------
        reference : list[float]
            Values from the reference distribution.
        current : list[float]
            Values from the current distribution.

        Returns
        -------
        tuple[float, float]
            ``(ks_statistic, p_value)``.  The statistic is the maximum
            absolute difference between the two CDFs.  The p-value is
            approximated using the Kolmogorov distribution.

        Raises
        ------
        ValueError
            If either list is empty.
        """
        if not reference or not current:
            raise ValueError("Both reference and current must be non-empty")

        n1 = len(reference)
        n2 = len(current)

        # Merge and sort all values, tracking which sample each came from
        combined = [(v, 0) for v in reference] + [(v, 1) for v in current]
        combined.sort(key=lambda x: x[0])

        cdf1 = 0.0
        cdf2 = 0.0
        d_max = 0.0

        for value, group in combined:
            if group == 0:
                cdf1 += 1.0 / n1
            else:
                cdf2 += 1.0 / n2
            d = abs(cdf1 - cdf2)
            if d > d_max:
                d_max = d

        # Approximate p-value using Kolmogorov distribution
        n_eff = math.sqrt(n1 * n2 / (n1 + n2))
        lambda_val = (n_eff + 0.12 + 0.11 / n_eff) * d_max

        # Kolmogorov survival function approximation
        if lambda_val == 0:
            p_value = 1.0
        else:
            p_value = 0.0
            for k in range(1, 101):
                sign = (-1) ** (k - 1)
                term = sign * math.exp(-2 * k * k * lambda_val * lambda_val)
                p_value += term
            p_value = max(0.0, min(1.0, 2.0 * p_value))

        logger.debug("KS test: D=%.6f, p=%.6f", d_max, p_value)
        return (d_max, p_value)

    @staticmethod
    def jensen_shannon_divergence(
        reference: List[float],
        current: List[float],
        num_bins: int = 10,
    ) -> float:
        """Calculate the Jensen-Shannon Divergence between two distributions.

        JSD is a symmetric, bounded measure of divergence.  It is the
        average of the KL divergences from each distribution to their
        midpoint distribution.

        Parameters
        ----------
        reference : list[float]
            Values from the reference distribution.
        current : list[float]
            Values from the current distribution.
        num_bins : int
            Number of equal-width bins (default 10).

        Returns
        -------
        float
            JSD value in [0, ln(2)].  Values > 0.1 typically indicate
            meaningful drift.

        Raises
        ------
        ValueError
            If either list is empty.
        """
        if not reference or not current:
            raise ValueError("Both reference and current must be non-empty")

        # Determine bin edges
        all_vals = reference + current
        min_val = min(all_vals)
        max_val = max(all_vals)

        if min_val == max_val:
            return 0.0

        bin_width = (max_val - min_val) / num_bins
        edges = [min_val + i * bin_width for i in range(num_bins + 1)]
        edges[-1] = max_val + 1e-10

        ref_counts = DriftDetector._bin_counts(reference, edges)
        cur_counts = DriftDetector._bin_counts(current, edges)

        # Convert to probability distributions with smoothing
        epsilon = 1e-10
        ref_total = sum(ref_counts) + epsilon * num_bins
        cur_total = sum(cur_counts) + epsilon * num_bins

        p = [(c + epsilon) / ref_total for c in ref_counts]
        q = [(c + epsilon) / cur_total for c in cur_counts]

        # Midpoint distribution
        m = [(p[i] + q[i]) / 2.0 for i in range(num_bins)]

        # JSD = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
        kl_pm = sum(p[i] * math.log(p[i] / m[i]) for i in range(num_bins))
        kl_qm = sum(q[i] * math.log(q[i] / m[i]) for i in range(num_bins))
        jsd = 0.5 * kl_pm + 0.5 * kl_qm

        logger.debug("JSD = %.6f (bins=%d)", jsd, num_bins)
        return jsd

    @staticmethod
    def is_drifted(
        score: float,
        method: str,
        threshold: Optional[float] = None,
    ) -> bool:
        """Determine whether a drift score indicates significant drift.

        Parameters
        ----------
        score : float
            The drift score (PSI value, KS p-value, or JSD value).
        method : str
            Detection method: ``"psi"``, ``"ks"``, or ``"jsd"``.
        threshold : float or None
            Custom threshold.  If ``None``, uses the default:
            PSI > 0.25, KS p-value < 0.05, JSD > 0.1.

        Returns
        -------
        bool
            ``True`` if the score indicates statistically significant drift.

        Raises
        ------
        ValueError
            If *method* is not recognised.
        """
        method_lower = method.lower()
        if method_lower not in _DEFAULT_THRESHOLDS:
            raise ValueError(
                f"Unknown method '{method}'. Must be one of: "
                f"{list(_DEFAULT_THRESHOLDS.keys())}"
            )

        thresh = threshold if threshold is not None else _DEFAULT_THRESHOLDS[method_lower]

        if method_lower == "ks":
            # For KS, the score is a p-value — drift if p < threshold
            drifted = score < thresh
        else:
            # For PSI and JSD, drift if score > threshold
            drifted = score > thresh

        logger.debug(
            "Drift check (%s): score=%.6f, threshold=%.6f, drifted=%s",
            method_lower,
            score,
            thresh,
            drifted,
        )
        return drifted

    # ── Internal helpers ──

    @staticmethod
    def _bin_counts(values: List[float], edges: List[float]) -> List[int]:
        """Count values falling into each bin defined by edges.

        Parameters
        ----------
        values : list[float]
            Data values to bin.
        edges : list[float]
            Bin edges of length ``num_bins + 1``.

        Returns
        -------
        list[int]
            Count per bin.
        """
        num_bins = len(edges) - 1
        counts = [0] * num_bins
        for v in values:
            # Binary search for the correct bin
            lo, hi = 0, num_bins - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if v < edges[mid + 1]:
                    hi = mid
                else:
                    lo = mid + 1
            counts[lo] += 1
        return counts
