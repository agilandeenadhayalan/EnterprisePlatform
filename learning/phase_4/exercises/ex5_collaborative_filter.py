"""
Exercise 5: Collaborative Filtering
========================================
User-based collaborative filtering recommends items by finding users
with similar tastes and suggesting what they liked.

The algorithm:
1. Compute cosine similarity between the target user and all others
2. Find the k most similar users (nearest neighbors)
3. For unrated items, predict a score as:
   score = sum(similarity_i * rating_i) / sum(similarity_i)
4. Return top-n items by predicted score

WHY COLLABORATIVE FILTERING:
It's the "people like you also liked..." approach. No need to understand
item content — the system learns purely from interaction patterns. This
is how early Netflix and Amazon recommendations worked.

YOUR TASK:
1. Implement cosine_similarity() — dot product / (norm_a * norm_b)
2. Implement find_k_nearest() — find most similar users
3. Implement recommend() — predict scores for unrated items
"""

import math


class SimpleCollaborativeFilter:
    """User-based collaborative filtering recommender."""

    def __init__(self, k: int = 3):
        self.k = k
        self._matrix: list[list[float]] = []
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []

    def fit(self, user_item_matrix: list[list[float]],
            user_ids: list[str], item_ids: list[str]):
        """Store the rating matrix.
        PROVIDED — do not modify.
        """
        self._matrix = [row[:] for row in user_item_matrix]
        self._user_ids = list(user_ids)
        self._item_ids = list(item_ids)

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two rating vectors.

        cosine(a, b) = (a . b) / (||a|| * ||b||)

        IMPORTANT: Only consider positions where BOTH vectors are non-zero.
        This handles sparsity — we only compare items both users rated.

        Args:
            vec_a: First user's rating vector.
            vec_b: Second user's rating vector.

        Returns:
            Cosine similarity (0.0 if no common ratings).
        """
        # TODO: Implement (~8 lines)
        # Hint: Loop through paired elements
        # Hint: Only accumulate when BOTH a and b are non-zero
        # Hint: Return 0.0 if either norm is 0
        raise NotImplementedError("Implement cosine similarity")

    def find_k_nearest(self, user_id: str) -> list[tuple[str, float]]:
        """Find the k users most similar to the given user.

        Args:
            user_id: Target user to find neighbors for.

        Returns:
            List of (neighbor_id, similarity) tuples, sorted by similarity
            descending. Only include users with similarity > 0.
        """
        # TODO: Implement (~8 lines)
        # Hint: Get the target user's row from the matrix
        # Hint: Compute cosine_similarity with every OTHER user
        # Hint: Sort by similarity descending, take top k
        raise NotImplementedError("Implement k-nearest neighbors")

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Recommend top-n items for a user.

        For each item the user has NOT rated:
          predicted_score = sum(sim_i * rating_i) / sum(sim_i)
        where the sum is over k-nearest neighbors who DID rate that item.

        Args:
            user_id: User to generate recommendations for.
            n: Number of recommendations to return.

        Returns:
            List of (item_id, predicted_score) tuples, sorted by score desc.
        """
        # TODO: Implement (~12 lines)
        # Hint: First call find_k_nearest to get neighbors
        # Hint: For each unrated item, accumulate weighted scores
        # Hint: Divide by sum of weights (similarities) to normalize
        raise NotImplementedError("Implement recommendation scoring")


# ── Verification ──

def _verify():
    """Run basic checks to verify your implementation."""
    # Small rating matrix: 5 users x 6 items
    matrix = [
        [5, 3, 0, 1, 0, 0],  # Alice
        [4, 0, 0, 1, 0, 0],  # Bob
        [1, 1, 0, 5, 0, 4],  # Carol
        [0, 0, 5, 4, 4, 0],  # Dave
        [0, 1, 4, 0, 5, 3],  # Eve
    ]
    users = ["alice", "bob", "carol", "dave", "eve"]
    items = ["i0", "i1", "i2", "i3", "i4", "i5"]

    cf = SimpleCollaborativeFilter(k=3)
    cf.fit(matrix, users, items)

    # Test 1: Cosine similarity
    sim = cf.cosine_similarity([1, 0, 0], [0, 1, 0])
    assert sim == 0.0, f"Expected 0.0 for orthogonal vectors, got {sim}"
    print("[PASS] Orthogonal vectors have similarity 0")

    sim = cf.cosine_similarity([1, 2, 3], [1, 2, 3])
    assert abs(sim - 1.0) < 0.001, f"Expected ~1.0 for identical vectors, got {sim}"
    print("[PASS] Identical vectors have similarity ~1")

    # Test 2: Find neighbors
    neighbors = cf.find_k_nearest("alice")
    assert len(neighbors) <= 3
    assert all(isinstance(uid, str) for uid, _ in neighbors)
    print(f"[PASS] Alice's neighbors: {neighbors}")

    # Test 3: Recommendations exclude rated items
    recs = cf.recommend("alice", n=3)
    rec_ids = {item_id for item_id, _ in recs}
    assert "i0" not in rec_ids, "Should not recommend already-rated items"
    assert "i1" not in rec_ids, "Should not recommend already-rated items"
    assert "i3" not in rec_ids, "Should not recommend already-rated items"
    print(f"[PASS] Recommendations for Alice: {recs}")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
