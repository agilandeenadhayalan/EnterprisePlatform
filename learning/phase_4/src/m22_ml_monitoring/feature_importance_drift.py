"""
Feature Importance Drift -- Detects shifts in which features matter most.

WHY THIS MATTERS:
Even if individual feature distributions are stable, the *relative
importance* of features can change. For example, a surge pricing model
might rely heavily on "time_of_day" during summer but shift to "weather"
in winter. Tracking importance drift reveals when the model's decision
logic no longer matches reality.

This module uses Spearman rank correlation to compare importance orderings
between a reference (training) period and the current production period.
"""


class FeatureImportanceDrift:
    """Detects when feature importance rankings change.

    Uses Spearman rank correlation to compare importance orderings between
    training and inference. Spearman correlation of 1.0 means identical
    rankings; values near 0 indicate no relationship; negative values
    indicate reversed rankings.

    WHY SPEARMAN:
    We care about the *ordering* of features, not their exact importance
    values. Spearman rank correlation is robust to monotonic transforms
    and focuses on whether the most important features remain most important.
    """

    def __init__(self):
        self._reference_importance: dict[str, float] = {}

    def set_reference_importance(self, feature_importances: dict[str, float]) -> None:
        """Store reference (training-time) feature importances."""
        if not feature_importances:
            raise ValueError("Feature importances must be non-empty")
        self._reference_importance = dict(feature_importances)

    def compute_current_importance(
        self, feature_importances: dict[str, float]
    ) -> dict:
        """Compare current importances against reference.

        Args:
            feature_importances: Current feature importance scores.

        Returns:
            dict with:
              - spearman_correlation: float (-1 to 1)
              - is_drifted: bool (True if correlation < 0.7)
              - shifted_features: list of features whose rank changed by > 2
        """
        if not self._reference_importance:
            raise RuntimeError("Must call set_reference_importance() first")

        # Find common features
        common_features = sorted(
            set(self._reference_importance.keys()) & set(feature_importances.keys())
        )

        if len(common_features) < 2:
            return {
                "spearman_correlation": 0.0,
                "is_drifted": True,
                "shifted_features": list(common_features),
            }

        # Rank features by importance (higher importance = rank 1)
        ref_ranks = self._rank_features(
            {f: self._reference_importance[f] for f in common_features}
        )
        cur_ranks = self._rank_features(
            {f: feature_importances[f] for f in common_features}
        )

        # Compute Spearman correlation
        ranks_a = [ref_ranks[f] for f in common_features]
        ranks_b = [cur_ranks[f] for f in common_features]
        correlation = self._spearman_correlation(ranks_a, ranks_b)

        # Find features with large rank shifts
        shifted_features = []
        for f in common_features:
            rank_diff = abs(ref_ranks[f] - cur_ranks[f])
            if rank_diff > 2:
                shifted_features.append(f)

        return {
            "spearman_correlation": correlation,
            "is_drifted": correlation < 0.7,
            "shifted_features": shifted_features,
        }

    def _spearman_correlation(self, ranks_a: list, ranks_b: list) -> float:
        """Compute Spearman rank correlation coefficient.

        Formula: rho = 1 - (6 * sum(d_i^2)) / (n * (n^2 - 1))
        where d_i = rank_a_i - rank_b_i

        This is equivalent to Pearson correlation applied to ranks.
        """
        n = len(ranks_a)
        if n < 2:
            return 0.0

        d_squared_sum = sum(
            (a - b) ** 2 for a, b in zip(ranks_a, ranks_b)
        )

        denominator = n * (n * n - 1)
        if denominator == 0:
            return 1.0

        return 1.0 - (6.0 * d_squared_sum) / denominator

    def _rank_features(self, importances: dict[str, float]) -> dict[str, int]:
        """Assign ranks to features (1 = most important)."""
        sorted_features = sorted(
            importances.keys(), key=lambda f: importances[f], reverse=True
        )
        return {f: rank + 1 for rank, f in enumerate(sorted_features)}
