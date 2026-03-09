"""
Collaborative Filtering -- Recommend items based on collective user behavior.

WHY THIS MATTERS:
Collaborative filtering is the backbone of most recommendation systems.
The key insight: users who agreed in the past will agree in the future.
No item content analysis needed -- only user-item interaction patterns.

Two flavors:
  - User-based: "Users like you also liked..."
  - Item-based: "Items similar to what you liked..."

Item-based CF tends to be more stable (item similarities change slowly)
while user-based CF captures emerging trends faster.
"""

import math


class UserBasedCF:
    """User-based collaborative filtering.

    Finds users with similar rating patterns (neighbors), then predicts
    ratings for unseen items as a weighted average of neighbors' ratings.

    WHY USER-BASED:
    User-based CF naturally captures the "people like you" intuition.
    Best for systems where user tastes cluster into groups (e.g., movie
    genres, music styles). Weakness: sparsity (most users rate few items).
    """

    def __init__(self, k_neighbors: int = 5):
        self.k_neighbors = k_neighbors
        self._matrix: list[list[float]] = []
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []
        self._user_index: dict[str, int] = {}
        self._item_index: dict[str, int] = {}

    def fit(
        self,
        user_item_matrix: list[list[float]],
        user_ids: list[str],
        item_ids: list[str],
    ) -> None:
        """Store the user-item interaction matrix.

        Args:
            user_item_matrix: Rows = users, columns = items. 0 = no interaction.
            user_ids: User identifiers corresponding to rows.
            item_ids: Item identifiers corresponding to columns.
        """
        self._matrix = [row[:] for row in user_item_matrix]
        self._user_ids = list(user_ids)
        self._item_ids = list(item_ids)
        self._user_index = {uid: i for i, uid in enumerate(user_ids)}
        self._item_index = {iid: i for i, iid in enumerate(item_ids)}

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        cosine(a, b) = (a . b) / (||a|| * ||b||)

        Only considers positions where BOTH vectors are non-zero,
        which handles the sparsity problem.
        """
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0

        for a, b in zip(vec_a, vec_b):
            if a != 0 and b != 0:
                dot += a * b
                norm_a += a * a
                norm_b += b * b

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def find_similar_users(self, user_id: str) -> list[tuple[str, float]]:
        """Find the k most similar users by cosine similarity.

        Returns:
            List of (user_id, similarity_score) tuples, sorted by similarity desc.
        """
        if user_id not in self._user_index:
            return []

        target_idx = self._user_index[user_id]
        target_vec = self._matrix[target_idx]

        similarities = []
        for uid, idx in self._user_index.items():
            if uid == user_id:
                continue
            sim = self._cosine_similarity(target_vec, self._matrix[idx])
            if sim > 0:
                similarities.append((uid, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[: self.k_neighbors]

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Recommend items for a user based on similar users' ratings.

        Strategy:
        1. Find k nearest neighbors
        2. For each item the target user hasn't rated:
           predicted_score = sum(sim_i * rating_i) / sum(sim_i)
        3. Return top-n by predicted score
        """
        if user_id not in self._user_index:
            return []

        target_idx = self._user_index[user_id]
        target_vec = self._matrix[target_idx]
        neighbors = self.find_similar_users(user_id)

        if not neighbors:
            return []

        scores: dict[str, float] = {}
        weights: dict[str, float] = {}

        for neighbor_id, similarity in neighbors:
            neighbor_idx = self._user_index[neighbor_id]
            for j, item_id in enumerate(self._item_ids):
                # Skip items the target user already rated
                if target_vec[j] != 0:
                    continue
                neighbor_rating = self._matrix[neighbor_idx][j]
                if neighbor_rating != 0:
                    scores[item_id] = scores.get(item_id, 0.0) + similarity * neighbor_rating
                    weights[item_id] = weights.get(item_id, 0.0) + similarity

        predictions = []
        for item_id in scores:
            if weights[item_id] > 0:
                predicted = scores[item_id] / weights[item_id]
                predictions.append((item_id, predicted))

        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]


class ItemBasedCF:
    """Item-based collaborative filtering.

    Finds items similar to those the user already liked, then recommends
    the most similar unseen items.

    WHY ITEM-BASED:
    Item similarities are more stable than user similarities (a movie's
    genre doesn't change, but user tastes evolve). Pre-computing item
    similarities enables faster real-time recommendations.
    """

    def __init__(self, k_neighbors: int = 5):
        self.k_neighbors = k_neighbors
        self._matrix: list[list[float]] = []
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []
        self._user_index: dict[str, int] = {}
        self._item_index: dict[str, int] = {}
        self._item_similarities: dict[str, list[tuple[str, float]]] = {}

    def fit(
        self,
        user_item_matrix: list[list[float]],
        user_ids: list[str],
        item_ids: list[str],
    ) -> None:
        """Store matrix and pre-compute item-item similarities."""
        self._matrix = [row[:] for row in user_item_matrix]
        self._user_ids = list(user_ids)
        self._item_ids = list(item_ids)
        self._user_index = {uid: i for i, uid in enumerate(user_ids)}
        self._item_index = {iid: i for i, iid in enumerate(item_ids)}
        self._precompute_similarities()

    def _precompute_similarities(self) -> None:
        """Compute pairwise item similarities using cosine similarity.

        Items are represented as column vectors in the user-item matrix,
        so item similarity is based on how similarly users rate them.
        """
        n_items = len(self._item_ids)

        for i in range(n_items):
            item_id = self._item_ids[i]
            col_i = [self._matrix[u][i] for u in range(len(self._user_ids))]
            sims = []

            for j in range(n_items):
                if i == j:
                    continue
                col_j = [self._matrix[u][j] for u in range(len(self._user_ids))]
                sim = self._cosine_similarity(col_i, col_j)
                if sim > 0:
                    sims.append((self._item_ids[j], sim))

            sims.sort(key=lambda x: x[1], reverse=True)
            self._item_similarities[item_id] = sims[: self.k_neighbors]

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two item column vectors."""
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0

        for a, b in zip(vec_a, vec_b):
            if a != 0 and b != 0:
                dot += a * b
                norm_a += a * a
                norm_b += b * b

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def find_similar_items(self, item_id: str) -> list[tuple[str, float]]:
        """Return pre-computed similar items."""
        return self._item_similarities.get(item_id, [])

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Recommend items based on items the user already liked.

        Strategy:
        1. For each item the user rated positively, find similar items
        2. Aggregate similarity scores for candidate items
        3. Exclude items already rated
        4. Return top-n candidates
        """
        if user_id not in self._user_index:
            return []

        user_idx = self._user_index[user_id]
        user_vec = self._matrix[user_idx]

        # Collect items the user has rated
        rated_items: set[str] = set()
        scores: dict[str, float] = {}
        weights: dict[str, float] = {}

        for j, item_id in enumerate(self._item_ids):
            rating = user_vec[j]
            if rating == 0:
                continue
            rated_items.add(item_id)

            for similar_id, sim in self.find_similar_items(item_id):
                if similar_id in rated_items:
                    continue
                scores[similar_id] = scores.get(similar_id, 0.0) + sim * rating
                weights[similar_id] = weights.get(similar_id, 0.0) + sim

        predictions = []
        for item_id in scores:
            if item_id not in rated_items and weights[item_id] > 0:
                predicted = scores[item_id] / weights[item_id]
                predictions.append((item_id, predicted))

        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]
