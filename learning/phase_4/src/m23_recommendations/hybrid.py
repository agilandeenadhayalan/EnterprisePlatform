"""
Hybrid Recommendations -- Best of both worlds.

WHY THIS MATTERS:
No single recommendation approach works well in all situations:
  - Collaborative filtering fails for cold-start users/items
  - Content-based filtering can't discover serendipitous items
  - Popularity-based is not personalized

A hybrid recommender combines multiple approaches, using weights to blend
their predictions. In practice, most production recommendation systems
are hybrids (Netflix, Spotify, Amazon all use ensemble approaches).

Common hybridization strategies:
  - Weighted: linear combination of scores from different models
  - Switching: use different model based on context (cold start vs. warm)
  - Feature augmentation: one model's output feeds into another
  - Cascade: coarse filter -> fine ranker

This module implements weighted hybridization.
"""

import math
from m23_recommendations.collaborative_filtering import UserBasedCF
from m23_recommendations.content_based import ContentBasedRecommender


class HybridRecommender:
    """Weighted combination of collaborative filtering and content-based scoring.

    Score = cf_weight * cf_score + cb_weight * cb_score

    Both scores are normalized to [0, 1] before combining, so the weights
    represent relative importance rather than absolute scales.

    WHY WEIGHTED HYBRID:
    Simple but effective. The weights can be tuned per user segment:
    - New users (few interactions): increase cb_weight
    - Active users (rich history): increase cf_weight
    """

    def __init__(self, cf_weight: float = 0.6, cb_weight: float = 0.4):
        if abs(cf_weight + cb_weight - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")
        self.cf_weight = cf_weight
        self.cb_weight = cb_weight
        self._cf = UserBasedCF()
        self._cb = ContentBasedRecommender()
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []

    def fit(
        self,
        user_item_matrix: list[list[float]],
        user_ids: list[str],
        item_ids: list[str],
        item_features: dict[str, dict[str, float]],
        user_interactions: dict[str, dict[str, float]],
    ) -> None:
        """Fit both sub-models.

        Args:
            user_item_matrix: Rating matrix for collaborative filtering.
            user_ids: User identifiers.
            item_ids: Item identifiers.
            item_features: Item feature vectors for content-based filtering.
            user_interactions: User-item interaction dict for content-based.
        """
        self._user_ids = list(user_ids)
        self._item_ids = list(item_ids)
        self._cf.fit(user_item_matrix, user_ids, item_ids)
        self._cb.fit(item_features, user_interactions)

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Generate hybrid recommendations by merging CF and CB scores.

        Steps:
        1. Get recommendations from both sub-models (larger candidate set)
        2. Normalize each set of scores to [0, 1]
        3. Merge using weighted combination
        4. Return top-n
        """
        # Get more candidates than needed from each model
        candidate_n = n * 3

        cf_scores = self._cf.recommend(user_id, candidate_n)
        cb_scores = self._cb.recommend(user_id, candidate_n)

        # Normalize scores
        cf_normalized = self._normalize_scores(cf_scores)
        cb_normalized = self._normalize_scores(cb_scores)

        # Merge
        merged = self._merge_scores(cf_normalized, cb_normalized)
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged[:n]

    def _normalize_scores(
        self, scores: list[tuple[str, float]]
    ) -> list[tuple[str, float]]:
        """Normalize scores to [0, 1] range using min-max scaling.

        This ensures CF and CB scores are on comparable scales before
        combining, preventing one model from dominating due to different
        score magnitudes.
        """
        if not scores:
            return []

        values = [s for _, s in scores]
        min_val = min(values)
        max_val = max(values)
        score_range = max_val - min_val

        if score_range == 0:
            return [(item_id, 1.0) for item_id, _ in scores]

        return [
            (item_id, (score - min_val) / score_range)
            for item_id, score in scores
        ]

    def _merge_scores(
        self,
        cf_scores: list[tuple[str, float]],
        cb_scores: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        """Merge normalized CF and CB scores using weighted combination.

        Items appearing in only one list get 0 for the missing score,
        which is appropriate since normalization maps to [0, 1].
        """
        score_map: dict[str, dict[str, float]] = {}

        for item_id, score in cf_scores:
            if item_id not in score_map:
                score_map[item_id] = {"cf": 0.0, "cb": 0.0}
            score_map[item_id]["cf"] = score

        for item_id, score in cb_scores:
            if item_id not in score_map:
                score_map[item_id] = {"cf": 0.0, "cb": 0.0}
            score_map[item_id]["cb"] = score

        merged = []
        for item_id, scores in score_map.items():
            combined = self.cf_weight * scores["cf"] + self.cb_weight * scores["cb"]
            merged.append((item_id, combined))

        return merged
