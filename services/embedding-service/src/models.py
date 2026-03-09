"""
Domain models for the Embedding service.
"""


class Embedding:
    """A feature vector embedding for an entity."""

    def __init__(
        self,
        entity_id: str,
        entity_type: str,
        vector: list[float],
        dimension: int | None = None,
        computed_at: str = "2026-03-09T12:00:00Z",
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.vector = vector
        self.dimension = dimension or len(vector)
        self.computed_at = computed_at

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "vector": self.vector,
            "dimension": self.dimension,
            "computed_at": self.computed_at,
        }


class SimilarityResult:
    """Results of a similarity search."""

    def __init__(
        self,
        query_id: str,
        results: list[dict],
    ):
        self.query_id = query_id
        self.results = results

    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "results": self.results,
        }


class KNNResult:
    """Results of a k-nearest neighbors search."""

    def __init__(
        self,
        query_id: str,
        k: int,
        neighbors: list[dict],
    ):
        self.query_id = query_id
        self.k = k
        self.neighbors = neighbors

    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "k": self.k,
            "neighbors": self.neighbors,
        }
