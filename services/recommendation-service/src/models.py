"""
Domain models for the Recommendation service.
"""


class Recommendation:
    """A set of recommended items with scores."""

    def __init__(
        self,
        entity_id: str,
        items: list[str],
        scores: list[float],
        strategy: str,
        generated_at: str = "2026-03-09T12:00:00Z",
    ):
        self.entity_id = entity_id
        self.items = items
        self.scores = scores
        self.strategy = strategy
        self.generated_at = generated_at

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "items": self.items,
            "scores": self.scores,
            "strategy": self.strategy,
            "generated_at": self.generated_at,
        }


class UserItemMatrix:
    """User-item interaction matrix for collaborative filtering."""

    def __init__(
        self,
        user_ids: list[str],
        item_ids: list[str],
        interactions: list[list[float]],
    ):
        self.user_ids = user_ids
        self.item_ids = item_ids
        self.interactions = interactions

    def to_dict(self) -> dict:
        return {
            "user_ids": self.user_ids,
            "item_ids": self.item_ids,
            "interactions": self.interactions,
        }


class SimilarEntity:
    """An entity similar to a query entity."""

    def __init__(
        self,
        entity_id: str,
        similarity_score: float,
    ):
        self.entity_id = entity_id
        self.similarity_score = similarity_score

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "similarity_score": self.similarity_score,
        }
