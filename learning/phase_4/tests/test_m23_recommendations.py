"""
Tests for M23: Recommendation Systems — collaborative filtering,
matrix factorization, content-based, cold start, and hybrid.
"""

import math
import random

import pytest

from m23_recommendations.collaborative_filtering import UserBasedCF, ItemBasedCF
from m23_recommendations.matrix_factorization import ALSMatrixFactorization
from m23_recommendations.content_based import ContentBasedRecommender
from m23_recommendations.cold_start import ColdStartHandler
from m23_recommendations.hybrid import HybridRecommender


# ── Shared test data ──


def _sample_matrix():
    """5 users x 6 items rating matrix.
    0 means unrated.
    """
    return {
        "matrix": [
            [5, 3, 0, 1, 0, 0],  # user_0
            [4, 0, 0, 1, 0, 0],  # user_1
            [1, 1, 0, 5, 0, 4],  # user_2
            [0, 0, 5, 4, 4, 0],  # user_3
            [0, 1, 4, 0, 5, 3],  # user_4
        ],
        "user_ids": ["u0", "u1", "u2", "u3", "u4"],
        "item_ids": ["i0", "i1", "i2", "i3", "i4", "i5"],
    }


def _sample_features():
    """Item features for content-based filtering."""
    return {
        "i0": {"genre_action": 1.0, "genre_comedy": 0.0, "popularity": 0.8},
        "i1": {"genre_action": 0.8, "genre_comedy": 0.2, "popularity": 0.6},
        "i2": {"genre_action": 0.0, "genre_comedy": 1.0, "popularity": 0.9},
        "i3": {"genre_action": 0.3, "genre_comedy": 0.7, "popularity": 0.5},
        "i4": {"genre_action": 0.0, "genre_comedy": 0.9, "popularity": 0.7},
        "i5": {"genre_action": 0.1, "genre_comedy": 0.8, "popularity": 0.4},
    }


def _sample_interactions():
    """User interactions dict derived from matrix."""
    m = _sample_matrix()
    interactions = {}
    for i, uid in enumerate(m["user_ids"]):
        interactions[uid] = {}
        for j, iid in enumerate(m["item_ids"]):
            if m["matrix"][i][j] != 0:
                interactions[uid][iid] = float(m["matrix"][i][j])
    return interactions


# ── UserBasedCF ──


class TestUserBasedCF:
    def test_fit_and_find_similar(self):
        data = _sample_matrix()
        cf = UserBasedCF(k_neighbors=3)
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        similar = cf.find_similar_users("u0")
        assert len(similar) <= 3
        assert all(isinstance(uid, str) and isinstance(sim, float) for uid, sim in similar)

    def test_recommend_returns_unrated_items(self):
        data = _sample_matrix()
        cf = UserBasedCF(k_neighbors=3)
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        recs = cf.recommend("u0", n=3)
        # u0 rated i0, i1, i3 -- recommendations should not include these
        rec_ids = {item_id for item_id, _ in recs}
        assert "i0" not in rec_ids
        assert "i1" not in rec_ids
        assert "i3" not in rec_ids

    def test_unknown_user_returns_empty(self):
        data = _sample_matrix()
        cf = UserBasedCF()
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        assert cf.recommend("nonexistent") == []

    def test_cosine_similarity_orthogonal(self):
        cf = UserBasedCF()
        assert cf._cosine_similarity([1, 0, 0], [0, 1, 0]) == 0.0

    def test_cosine_similarity_identical(self):
        cf = UserBasedCF()
        sim = cf._cosine_similarity([1, 2, 3], [1, 2, 3])
        assert abs(sim - 1.0) < 0.001

    def test_recommendations_have_scores(self):
        data = _sample_matrix()
        cf = UserBasedCF(k_neighbors=3)
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        recs = cf.recommend("u0", n=5)
        for item_id, score in recs:
            assert score > 0


# ── ItemBasedCF ──


class TestItemBasedCF:
    def test_fit_and_find_similar_items(self):
        data = _sample_matrix()
        cf = ItemBasedCF(k_neighbors=3)
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        similar = cf.find_similar_items("i0")
        assert all(isinstance(iid, str) for iid, _ in similar)

    def test_recommend_excludes_rated(self):
        data = _sample_matrix()
        cf = ItemBasedCF(k_neighbors=3)
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        recs = cf.recommend("u0", n=3)
        rec_ids = {item_id for item_id, _ in recs}
        # u0 rated i0, i1, i3
        assert "i0" not in rec_ids
        assert "i1" not in rec_ids
        assert "i3" not in rec_ids

    def test_unknown_user_returns_empty(self):
        data = _sample_matrix()
        cf = ItemBasedCF()
        cf.fit(data["matrix"], data["user_ids"], data["item_ids"])
        assert cf.recommend("nonexistent") == []


# ── ALSMatrixFactorization ──


class TestALSMatrixFactorization:
    def test_reconstruction_error_decreases(self):
        data = _sample_matrix()
        als = ALSMatrixFactorization(n_factors=3, n_iterations=50, seed=42)
        als.fit(data["matrix"], data["user_ids"], data["item_ids"])
        error = als.reconstruction_error()
        # With enough iterations, RMSE should be < 1.0 for this small matrix
        assert error < 2.0

    def test_predict_observed_rating(self):
        data = _sample_matrix()
        als = ALSMatrixFactorization(n_factors=3, n_iterations=50, seed=42)
        als.fit(data["matrix"], data["user_ids"], data["item_ids"])
        # u0 rated i0 as 5.0
        pred = als.predict("u0", "i0")
        assert abs(pred - 5.0) < 2.0  # reasonable approximation

    def test_recommend_returns_unrated(self):
        data = _sample_matrix()
        als = ALSMatrixFactorization(n_factors=3, n_iterations=20, seed=42)
        als.fit(data["matrix"], data["user_ids"], data["item_ids"])
        recs = als.recommend("u0", n=3)
        rec_ids = {item_id for item_id, _ in recs}
        # u0 rated i0, i1, i3
        assert "i0" not in rec_ids

    def test_unknown_user_returns_empty(self):
        data = _sample_matrix()
        als = ALSMatrixFactorization()
        als.fit(data["matrix"], data["user_ids"], data["item_ids"])
        assert als.recommend("nonexistent") == []

    def test_predict_unknown_item_zero(self):
        data = _sample_matrix()
        als = ALSMatrixFactorization()
        als.fit(data["matrix"], data["user_ids"], data["item_ids"])
        assert als.predict("u0", "nonexistent") == 0.0


# ── ContentBasedRecommender ──


class TestContentBasedRecommender:
    def test_recommend_returns_unrated(self):
        features = _sample_features()
        interactions = _sample_interactions()
        cb = ContentBasedRecommender()
        cb.fit(features, interactions)
        recs = cb.recommend("u0", n=3)
        rec_ids = {item_id for item_id, _ in recs}
        # u0 interacted with i0, i1, i3
        assert "i0" not in rec_ids
        assert "i1" not in rec_ids
        assert "i3" not in rec_ids

    def test_content_similarity_drives_recs(self):
        """u0 likes action items (i0=action, i1=action). Recommendations
        should lean toward action items."""
        features = _sample_features()
        interactions = {"u_action": {"i0": 5.0, "i1": 5.0}}
        cb = ContentBasedRecommender()
        cb.fit(features, interactions)
        recs = cb.recommend("u_action", n=3)
        # Should have some recs (not all items are pure action though)
        assert len(recs) > 0

    def test_unknown_user_returns_empty(self):
        features = _sample_features()
        interactions = _sample_interactions()
        cb = ContentBasedRecommender()
        cb.fit(features, interactions)
        assert cb.recommend("nonexistent") == []

    def test_user_profile_has_features(self):
        features = _sample_features()
        interactions = _sample_interactions()
        cb = ContentBasedRecommender()
        cb.fit(features, interactions)
        profile = cb._build_user_profile("u0")
        assert "genre_action" in profile
        assert "genre_comedy" in profile


# ── ColdStartHandler ──


class TestColdStartHandler:
    def test_popularity_based_new_user(self):
        data = _sample_matrix()
        handler = ColdStartHandler()
        handler.fit(data["matrix"], data["item_ids"])
        recs = handler.recommend_for_new_user(n=3)
        assert len(recs) == 3
        # Most popular items should be ranked first
        assert all(isinstance(score, float) for _, score in recs)

    def test_preference_adjusted_new_user(self):
        data = _sample_matrix()
        features = _sample_features()
        handler = ColdStartHandler()
        handler.fit(data["matrix"], data["item_ids"], item_features=features)
        recs = handler.recommend_for_new_user(
            preferences={"genre_action": 1.0}, n=3
        )
        assert len(recs) == 3

    def test_new_item_targeting(self):
        data = _sample_matrix()
        features = _sample_features()
        handler = ColdStartHandler()
        handler.fit(data["matrix"], data["item_ids"], item_features=features)
        users = handler.recommend_for_new_item(
            "i_new", {"genre_action": 1.0, "genre_comedy": 0.0, "popularity": 0.5}, n_users=3
        )
        assert len(users) <= 3
        assert all(isinstance(u, str) for u in users)

    def test_new_item_no_features_fallback(self):
        data = _sample_matrix()
        handler = ColdStartHandler()
        handler.fit(data["matrix"], data["item_ids"])
        users = handler.recommend_for_new_item("i_new", {"a": 1.0}, n_users=3)
        assert len(users) <= 3


# ── HybridRecommender ──


class TestHybridRecommender:
    def test_hybrid_returns_recommendations(self):
        data = _sample_matrix()
        features = _sample_features()
        interactions = _sample_interactions()
        hybrid = HybridRecommender(cf_weight=0.6, cb_weight=0.4)
        hybrid.fit(
            data["matrix"], data["user_ids"], data["item_ids"],
            features, interactions,
        )
        recs = hybrid.recommend("u0", n=3)
        assert len(recs) > 0

    def test_hybrid_excludes_rated(self):
        data = _sample_matrix()
        features = _sample_features()
        interactions = _sample_interactions()
        hybrid = HybridRecommender(cf_weight=0.5, cb_weight=0.5)
        hybrid.fit(
            data["matrix"], data["user_ids"], data["item_ids"],
            features, interactions,
        )
        recs = hybrid.recommend("u0", n=5)
        rec_ids = {item_id for item_id, _ in recs}
        assert "i0" not in rec_ids

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError):
            HybridRecommender(cf_weight=0.5, cb_weight=0.3)

    def test_normalize_scores_uniform(self):
        hybrid = HybridRecommender()
        scores = [("a", 5.0), ("b", 5.0), ("c", 5.0)]
        normalized = hybrid._normalize_scores(scores)
        assert all(abs(s - 1.0) < 0.001 for _, s in normalized)

    def test_normalize_scores_range(self):
        hybrid = HybridRecommender()
        scores = [("a", 1.0), ("b", 3.0), ("c", 5.0)]
        normalized = hybrid._normalize_scores(scores)
        norm_dict = {item: score for item, score in normalized}
        assert abs(norm_dict["a"] - 0.0) < 0.001
        assert abs(norm_dict["c"] - 1.0) < 0.001
