"""
Cold Start Handling -- Strategies for new users and new items.

WHY THIS MATTERS:
The cold start problem is the Achilles' heel of recommendation systems.
When a new user joins, we have no interaction history. When a new item
is added, no one has rated it yet. Both cases break collaborative filtering.

Strategies:
  - New users: popularity-based fallback, optionally adjusted by stated preferences
  - New items: feature-based matching to find users who liked similar items

For a mobility platform:
  - New rider: recommend popular routes/times until enough trip data accumulates
  - New route/zone: match to riders who use similar existing routes
"""

import math


class ColdStartHandler:
    """Handles the cold start problem for new users and new items.

    WHY COLD START IS HARD:
    Collaborative filtering needs interaction data. New users have none,
    and new items have none. The system must gracefully degrade to simpler
    strategies while still providing reasonable recommendations.

    This handler provides:
    1. Popularity-based recommendations for new users
    2. Feature-based user targeting for new items
    """

    def __init__(self):
        self._item_popularity: list[tuple[str, float]] = []
        self._item_ids: list[str] = []
        self._user_item_matrix: list[list[float]] = []
        self._item_features: dict[str, dict] = {}
        self._user_ids: list[str] = []

    def fit(
        self,
        user_item_matrix: list[list[float]],
        item_ids: list[str],
        item_features: dict[str, dict] = None,
    ) -> None:
        """Learn popularity scores and item feature mappings.

        Args:
            user_item_matrix: Rows = users, columns = items.
            item_ids: Item identifiers.
            item_features: Optional {item_id: {feature: value}} for
                          content-based new-item handling.
        """
        self._user_item_matrix = [row[:] for row in user_item_matrix]
        self._item_ids = list(item_ids)
        self._item_features = dict(item_features) if item_features else {}
        self._user_ids = [f"user_{i}" for i in range(len(user_item_matrix))]

        # Compute item popularity: number of non-zero interactions + average rating
        popularity = []
        for j, item_id in enumerate(item_ids):
            ratings = [row[j] for row in user_item_matrix if row[j] != 0]
            if ratings:
                count = len(ratings)
                avg = sum(ratings) / count
                # Popularity score combines frequency and average rating
                score = count * avg
                popularity.append((item_id, score))
            else:
                popularity.append((item_id, 0.0))

        popularity.sort(key=lambda x: x[1], reverse=True)
        self._item_popularity = popularity

    def recommend_for_new_user(
        self, preferences: dict = None, n: int = 5
    ) -> list[tuple[str, float]]:
        """Recommend items for a brand-new user.

        Uses popularity-based fallback, optionally adjusted by stated
        preferences (e.g., from an onboarding survey).

        Args:
            preferences: Optional dict of {feature: preferred_value} from
                        user onboarding. Used to filter/re-rank popular items.
            n: Number of recommendations.

        Returns:
            List of (item_id, score) tuples.
        """
        if not self._item_popularity:
            return []

        if preferences and self._item_features:
            # Re-rank popular items by preference match
            scored = []
            for item_id, pop_score in self._item_popularity:
                if item_id not in self._item_features:
                    scored.append((item_id, pop_score))
                    continue

                features = self._item_features[item_id]
                # Boost score if item features match preferences
                match_bonus = 0.0
                for pref_feature, pref_value in preferences.items():
                    if pref_feature in features:
                        if isinstance(pref_value, (int, float)) and isinstance(
                            features[pref_feature], (int, float)
                        ):
                            # Numerical: closer = better match
                            diff = abs(features[pref_feature] - pref_value)
                            match_bonus += max(0, 1.0 - diff)
                        elif features[pref_feature] == pref_value:
                            # Categorical: exact match
                            match_bonus += 1.0

                combined = pop_score * (1.0 + match_bonus)
                scored.append((item_id, combined))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:n]

        # Pure popularity fallback
        return self._item_popularity[:n]

    def recommend_for_new_item(
        self, item_id: str, item_features: dict, n_users: int = 5
    ) -> list[str]:
        """Find users most likely to enjoy a new item.

        Strategy: Find existing items with similar features, then identify
        users who rated those items highly.

        Args:
            item_id: Identifier for the new item.
            item_features: {feature: value} for the new item.
            n_users: Number of users to target.

        Returns:
            List of user identifiers most likely to enjoy the item.
        """
        if not self._item_features:
            # No feature data: return users with most interactions
            interaction_counts = []
            for i, row in enumerate(self._user_item_matrix):
                count = sum(1 for v in row if v != 0)
                interaction_counts.append((self._user_ids[i], count))
            interaction_counts.sort(key=lambda x: x[1], reverse=True)
            return [uid for uid, _ in interaction_counts[:n_users]]

        # Find similar existing items by feature similarity
        similar_items = []
        for existing_id, existing_features in self._item_features.items():
            if existing_id == item_id:
                continue
            sim = self._feature_similarity(item_features, existing_features)
            if sim > 0:
                similar_items.append((existing_id, sim))

        similar_items.sort(key=lambda x: x[1], reverse=True)
        top_similar = similar_items[:5]

        if not top_similar:
            return []

        # Find users who rated similar items highly
        user_scores: dict[str, float] = {}
        for similar_id, sim in top_similar:
            if similar_id not in self._item_ids:
                continue
            j = self._item_ids.index(similar_id)
            for i, row in enumerate(self._user_item_matrix):
                if row[j] > 0:
                    uid = self._user_ids[i]
                    user_scores[uid] = user_scores.get(uid, 0.0) + sim * row[j]

        ranked_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
        return [uid for uid, _ in ranked_users[:n_users]]

    def _feature_similarity(self, features_a: dict, features_b: dict) -> float:
        """Compute cosine similarity between two feature dictionaries."""
        common_keys = set(features_a.keys()) & set(features_b.keys())
        if not common_keys:
            return 0.0

        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0

        for key in common_keys:
            a = features_a[key]
            b = features_b[key]
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                dot += a * b
                norm_a += a * a
                norm_b += b * b

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
