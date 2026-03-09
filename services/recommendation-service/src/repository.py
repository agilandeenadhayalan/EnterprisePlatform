"""
In-memory recommendation repository with collaborative filtering,
content-based, and hybrid recommendation logic. Pre-seeded data.
"""

import math
import random
from models import Recommendation, UserItemMatrix, SimilarEntity


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class RecommendationRepository:
    """In-memory store for recommendation data and logic."""

    def __init__(self, seed: bool = False):
        self.driver_ids: list[str] = []
        self.zone_ids: list[str] = []
        self.interaction_matrix: list[list[float]] = []
        self.zone_metadata: dict[str, dict] = {}
        self.popular_by_hour: dict[int, list[str]] = {}
        if seed:
            self._seed()

    def _seed(self):
        rng = random.Random(42)

        # 15 drivers x 20 zones
        self.driver_ids = [f"driver_{i:03d}" for i in range(1, 16)]
        self.zone_ids = [f"zone_{i:02d}" for i in range(1, 21)]

        # User-item interaction matrix: ride counts
        # Each driver has a pattern of preferred zones
        self.interaction_matrix = []
        for i in range(15):
            row = []
            # Each driver has 3-5 preferred zones with high counts
            preferred = rng.sample(range(20), rng.randint(3, 5))
            for j in range(20):
                if j in preferred:
                    row.append(float(rng.randint(8, 25)))
                else:
                    row.append(float(rng.randint(0, 4)))
            self.interaction_matrix.append(row)

        # Zone metadata
        boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
        demand_levels = ["low", "medium", "high", "very_high"]
        for i, zone_id in enumerate(self.zone_ids):
            self.zone_metadata[zone_id] = {
                "avg_fare": round(rng.gauss(18.0, 6.0), 2),
                "demand_level": demand_levels[i % len(demand_levels)],
                "borough": boroughs[i % len(boroughs)],
                "avg_trip_distance": round(rng.gauss(5.0, 2.0), 2),
                "avg_tip_pct": round(rng.uniform(0.10, 0.25), 2),
            }

        # Popular zones by hour (6-23)
        for hour in range(6, 24):
            if 7 <= hour <= 9:  # Morning rush
                top_zones = ["zone_01", "zone_03", "zone_05", "zone_07", "zone_10"]
            elif 11 <= hour <= 14:  # Lunch
                top_zones = ["zone_02", "zone_04", "zone_06", "zone_08", "zone_12"]
            elif 17 <= hour <= 19:  # Evening rush
                top_zones = ["zone_01", "zone_02", "zone_09", "zone_11", "zone_15"]
            else:
                top_zones = ["zone_03", "zone_06", "zone_10", "zone_14", "zone_18"]
            self.popular_by_hour[hour] = top_zones

    # ── Collaborative filtering ──

    def _get_driver_index(self, driver_id: str) -> int | None:
        if driver_id in self.driver_ids:
            return self.driver_ids.index(driver_id)
        return None

    def _collaborative_recommend(self, driver_id: str, k_neighbors: int = 5,
                                  n_recommendations: int = 5) -> Recommendation | None:
        """User-based collaborative filtering using cosine similarity."""
        idx = self._get_driver_index(driver_id)
        if idx is None:
            return None

        target_vector = self.interaction_matrix[idx]

        # Find similar drivers
        similarities = []
        for i, driver in enumerate(self.driver_ids):
            if i == idx:
                continue
            sim = _cosine_similarity(target_vector, self.interaction_matrix[i])
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_neighbors = similarities[:k_neighbors]

        # Aggregate neighbor preferences weighted by similarity
        zone_scores: dict[int, float] = {}
        for neighbor_idx, sim in top_neighbors:
            for j in range(len(self.zone_ids)):
                if target_vector[j] == 0:  # Only recommend zones driver hasn't visited much
                    zone_scores[j] = zone_scores.get(j, 0.0) + sim * self.interaction_matrix[neighbor_idx][j]

        # If no unvisited zones, fall back to all zones
        if not zone_scores:
            for neighbor_idx, sim in top_neighbors:
                for j in range(len(self.zone_ids)):
                    zone_scores[j] = zone_scores.get(j, 0.0) + sim * self.interaction_matrix[neighbor_idx][j]

        ranked = sorted(zone_scores.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        items = [self.zone_ids[j] for j, _ in ranked]
        scores = [round(s, 4) for _, s in ranked]

        return Recommendation(
            entity_id=driver_id,
            items=items,
            scores=scores,
            strategy="collaborative",
        )

    # ── Content-based ──

    def _content_based_recommend(self, driver_id: str, n_recommendations: int = 5) -> Recommendation | None:
        """Content-based filtering using zone feature similarity."""
        idx = self._get_driver_index(driver_id)
        if idx is None:
            return None

        target_vector = self.interaction_matrix[idx]

        # Find driver's preferred zone profile (weighted avg of zone features)
        total_rides = sum(target_vector)
        if total_rides == 0:
            return None

        pref_fare = 0.0
        pref_distance = 0.0
        pref_tip = 0.0
        for j, count in enumerate(target_vector):
            meta = self.zone_metadata[self.zone_ids[j]]
            weight = count / total_rides
            pref_fare += meta["avg_fare"] * weight
            pref_distance += meta["avg_trip_distance"] * weight
            pref_tip += meta["avg_tip_pct"] * weight

        # Score zones by similarity to driver's preference profile
        zone_scores = []
        for j, zone_id in enumerate(self.zone_ids):
            meta = self.zone_metadata[zone_id]
            zone_vec = [meta["avg_fare"], meta["avg_trip_distance"], meta["avg_tip_pct"]]
            pref_vec = [pref_fare, pref_distance, pref_tip]
            sim = _cosine_similarity(zone_vec, pref_vec)
            zone_scores.append((zone_id, sim))

        zone_scores.sort(key=lambda x: x[1], reverse=True)
        top = zone_scores[:n_recommendations]

        return Recommendation(
            entity_id=driver_id,
            items=[z for z, _ in top],
            scores=[round(s, 4) for _, s in top],
            strategy="content_based",
        )

    # ── Hybrid ──

    def _hybrid_recommend(self, driver_id: str, n_recommendations: int = 5,
                           collab_weight: float = 0.6) -> Recommendation:
        """Hybrid recommendation: weighted combination of collaborative + content-based."""
        collab = self._collaborative_recommend(driver_id, n_recommendations=n_recommendations * 2)
        content = self._content_based_recommend(driver_id, n_recommendations=n_recommendations * 2)

        # Merge scores
        combined: dict[str, float] = {}
        if collab:
            max_collab = max(collab.scores) if collab.scores else 1.0
            for item, score in zip(collab.items, collab.scores):
                normalized = score / max_collab if max_collab > 0 else 0.0
                combined[item] = combined.get(item, 0.0) + collab_weight * normalized

        content_weight = 1.0 - collab_weight
        if content:
            for item, score in zip(content.items, content.scores):
                combined[item] = combined.get(item, 0.0) + content_weight * score

        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        return Recommendation(
            entity_id=driver_id,
            items=[item for item, _ in ranked],
            scores=[round(score, 4) for _, score in ranked],
            strategy="hybrid",
        )

    # ── Public API ──

    def recommend_for_driver(self, driver_id: str) -> Recommendation:
        """Get zone recommendations for a driver using hybrid approach."""
        idx = self._get_driver_index(driver_id)
        if idx is None:
            return self._cold_start_recommend(driver_id, "driver")
        return self._hybrid_recommend(driver_id)

    def recommend_for_rider(self, rider_id: str) -> Recommendation:
        """Get zone recommendations for a rider (popularity-based)."""
        # Riders use popularity-based since they don't have interaction history
        popular = self.get_popular_zones(hour=12)
        return Recommendation(
            entity_id=rider_id,
            items=[z["zone_id"] for z in popular[:5]],
            scores=[z["score"] for z in popular[:5]],
            strategy="popularity",
        )

    def get_popular_zones(self, hour: int | None = None, day: int | None = None) -> list[dict]:
        """Get popular pickup zones optionally filtered by hour/day."""
        if hour is not None and hour in self.popular_by_hour:
            zone_list = self.popular_by_hour[hour]
        else:
            # Aggregate across all hours
            zone_counts: dict[str, int] = {}
            for zones in self.popular_by_hour.values():
                for z in zones:
                    zone_counts[z] = zone_counts.get(z, 0) + 1
            zone_list = sorted(zone_counts.keys(), key=lambda z: zone_counts[z], reverse=True)

        result = []
        for i, zone_id in enumerate(zone_list):
            meta = self.zone_metadata.get(zone_id, {})
            result.append({
                "zone_id": zone_id,
                "score": round(1.0 - i * 0.1, 2),
                "avg_fare": meta.get("avg_fare", 0.0),
                "demand_level": meta.get("demand_level", "unknown"),
            })
        return result

    def find_similar_drivers(self, driver_id: str, k: int = 5) -> list[SimilarEntity]:
        """Find drivers with similar ride patterns using cosine similarity."""
        idx = self._get_driver_index(driver_id)
        if idx is None:
            return []

        target_vector = self.interaction_matrix[idx]
        similarities = []
        for i, driver in enumerate(self.driver_ids):
            if i == idx:
                continue
            sim = _cosine_similarity(target_vector, self.interaction_matrix[i])
            similarities.append(SimilarEntity(entity_id=driver, similarity_score=round(sim, 4)))

        similarities.sort(key=lambda x: x.similarity_score, reverse=True)
        return similarities[:k]

    def _cold_start_recommend(self, entity_id: str, user_type: str,
                                preferences: dict | None = None) -> Recommendation:
        """Popularity-based fallback for new users."""
        popular = self.get_popular_zones()
        items = [z["zone_id"] for z in popular[:5]]
        scores = [z["score"] for z in popular[:5]]

        # If preferences provided, re-weight by preference match
        if preferences:
            weighted = []
            for i, zone_id in enumerate(items):
                meta = self.zone_metadata.get(zone_id, {})
                boost = 1.0
                if "preferred_fare" in preferences:
                    fare_diff = abs(meta.get("avg_fare", 15.0) - preferences["preferred_fare"])
                    boost *= max(0.5, 1.0 - fare_diff / 30.0)
                if "preferred_borough" in preferences:
                    if meta.get("borough") == preferences["preferred_borough"]:
                        boost *= 1.5
                weighted.append((zone_id, round(scores[i] * boost, 4)))
            weighted.sort(key=lambda x: x[1], reverse=True)
            items = [w[0] for w in weighted]
            scores = [w[1] for w in weighted]

        return Recommendation(
            entity_id=entity_id,
            items=items,
            scores=scores,
            strategy="cold_start",
        )

    def cold_start_recommend(self, user_type: str,
                              preferences: dict | None = None) -> Recommendation:
        """Public cold start recommendation for new users."""
        return self._cold_start_recommend("new_user", user_type, preferences)


REPO_CLASS = RecommendationRepository
repo = RecommendationRepository(seed=True)
