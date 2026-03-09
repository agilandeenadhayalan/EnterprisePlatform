"""
Content-Based Recommendations -- Recommend items similar to what the user liked.

WHY THIS MATTERS:
Collaborative filtering fails when there are few user interactions (cold
start). Content-based filtering uses item features (genre, price, location)
to recommend items similar to a user's past preferences. It doesn't need
other users' data at all.

For a mobility platform: ride features might include distance, time_of_day,
pickup_zone, vehicle_type, etc. A user who frequently books premium rides
at airports would get recommended similar premium rides.
"""

import math


class ContentBasedRecommender:
    """Recommends items similar to user's past preferences based on item features.

    Algorithm:
    1. Build a user profile as a weighted average of features from items
       they've interacted with (weighted by interaction strength/rating).
    2. Score candidate items by cosine similarity between user profile
       and item feature vectors.
    3. Return top-scoring items the user hasn't seen.

    WHY CONTENT-BASED:
    - Works with a single user's history (no cold-start for items with features)
    - Transparent: can explain "recommended because you liked X feature"
    - No popularity bias (can recommend niche items)
    - Limitation: won't discover items outside user's feature preferences
    """

    def __init__(self):
        self._item_features: dict[str, dict[str, float]] = {}
        self._user_interactions: dict[str, dict[str, float]] = {}
        self._user_profiles: dict[str, dict[str, float]] = {}
        self._all_features: list[str] = []

    def fit(
        self,
        item_features: dict[str, dict[str, float]],
        user_interactions: dict[str, dict[str, float]],
    ) -> None:
        """Fit the recommender with item features and user interaction history.

        Args:
            item_features: {item_id: {feature_name: feature_value, ...}}
            user_interactions: {user_id: {item_id: rating/interaction_score, ...}}
        """
        self._item_features = {k: dict(v) for k, v in item_features.items()}
        self._user_interactions = {k: dict(v) for k, v in user_interactions.items()}

        # Collect all feature names
        feature_set: set[str] = set()
        for features in item_features.values():
            feature_set.update(features.keys())
        self._all_features = sorted(feature_set)

        # Build user profiles
        self._user_profiles = {}
        for user_id in user_interactions:
            self._user_profiles[user_id] = self._build_user_profile(user_id)

    def _build_user_profile(self, user_id: str) -> dict[str, float]:
        """Build a user profile as weighted average of interacted item features.

        For each feature, the profile value is:
          sum(rating_i * feature_value_i) / sum(rating_i)

        This creates a "centroid" of the user's preferred items in feature space.
        """
        interactions = self._user_interactions.get(user_id, {})
        if not interactions:
            return {}

        profile: dict[str, float] = {f: 0.0 for f in self._all_features}
        total_weight = 0.0

        for item_id, rating in interactions.items():
            if item_id not in self._item_features:
                continue
            features = self._item_features[item_id]
            for feature_name in self._all_features:
                value = features.get(feature_name, 0.0)
                profile[feature_name] += rating * value
            total_weight += abs(rating)

        if total_weight > 0:
            for f in profile:
                profile[f] /= total_weight

        return profile

    def _item_similarity(self, profile: dict[str, float], item_features: dict[str, float]) -> float:
        """Compute cosine similarity between user profile and item feature vector."""
        dot = 0.0
        norm_p = 0.0
        norm_i = 0.0

        for f in self._all_features:
            p_val = profile.get(f, 0.0)
            i_val = item_features.get(f, 0.0)
            dot += p_val * i_val
            norm_p += p_val * p_val
            norm_i += i_val * i_val

        if norm_p == 0 or norm_i == 0:
            return 0.0

        return dot / (math.sqrt(norm_p) * math.sqrt(norm_i))

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Recommend items for a user based on content similarity.

        Returns:
            List of (item_id, similarity_score), sorted by score descending.
        """
        if user_id not in self._user_profiles:
            return []

        profile = self._user_profiles[user_id]
        if not profile:
            return []

        interacted = set(self._user_interactions.get(user_id, {}).keys())
        candidates = []

        for item_id, features in self._item_features.items():
            if item_id in interacted:
                continue
            sim = self._item_similarity(profile, features)
            if sim > 0:
                candidates.append((item_id, sim))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:n]
