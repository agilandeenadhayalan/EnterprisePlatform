"""
In-memory embedding repository with pre-seeded data.
"""

import math
import random
from models import Embedding, SimilarityResult, KNNResult


def _normalize(vector: list[float]) -> list[float]:
    """L2-normalize a vector."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingRepository:
    """In-memory store for entity embeddings."""

    def __init__(self, seed: bool = False):
        self.embeddings: dict[str, Embedding] = {}  # key: "{entity_type}:{entity_id}"
        if seed:
            self._seed()

    def _seed(self):
        rng = random.Random(42)

        # 15 drivers with 8-dimensional embeddings
        for i in range(1, 16):
            entity_id = f"driver_{i:03d}"
            vec = [round(rng.gauss(0, 1), 4) for _ in range(8)]
            vec = [round(v, 4) for v in _normalize(vec)]
            key = f"driver:{entity_id}"
            self.embeddings[key] = Embedding(
                entity_id=entity_id,
                entity_type="driver",
                vector=vec,
                computed_at="2026-03-09T10:00:00Z",
            )

        # 20 zones with 6-dimensional embeddings
        for i in range(1, 21):
            entity_id = f"zone_{i:02d}"
            vec = [round(rng.gauss(0, 1), 4) for _ in range(6)]
            vec = [round(v, 4) for v in _normalize(vec)]
            key = f"zone:{entity_id}"
            self.embeddings[key] = Embedding(
                entity_id=entity_id,
                entity_type="zone",
                vector=vec,
                computed_at="2026-03-09T10:00:00Z",
            )

    def _make_key(self, entity_type: str, entity_id: str) -> str:
        return f"{entity_type}:{entity_id}"

    # ── Compute ──

    def compute_embedding(self, entity_type: str, entity_id: str,
                           features: dict[str, float]) -> Embedding:
        """Compute embedding from features: normalize and store."""
        values = list(features.values())
        vector = [round(v, 4) for v in _normalize(values)]
        emb = Embedding(
            entity_id=entity_id,
            entity_type=entity_type,
            vector=vector,
        )
        key = self._make_key(entity_type, entity_id)
        self.embeddings[key] = emb
        return emb

    def compute_batch(self, entities: list[dict]) -> list[Embedding]:
        """Compute embeddings for a batch of entities."""
        results = []
        for e in entities:
            emb = self.compute_embedding(e["entity_type"], e["entity_id"], e["features"])
            results.append(emb)
        return results

    # ── Retrieve ──

    def get_embedding(self, entity_type: str, entity_id: str) -> Embedding | None:
        key = self._make_key(entity_type, entity_id)
        return self.embeddings.get(key)

    # ── Similarity ──

    def find_similar(self, entity_type: str, entity_id: str,
                      k: int = 5) -> SimilarityResult:
        """Find similar entities using cosine similarity."""
        key = self._make_key(entity_type, entity_id)
        query_emb = self.embeddings.get(key)
        if not query_emb:
            return SimilarityResult(query_id=entity_id, results=[])

        similarities = []
        for emb_key, emb in self.embeddings.items():
            if emb_key == key:
                continue
            if emb.entity_type != entity_type:
                continue
            score = _cosine_similarity(query_emb.vector, emb.vector)
            similarities.append({"entity_id": emb.entity_id, "score": round(score, 4)})

        similarities.sort(key=lambda x: x["score"], reverse=True)
        return SimilarityResult(query_id=entity_id, results=similarities[:k])

    # ── KNN ──

    def knn_search(self, query_vector: list[float], k: int = 5) -> KNNResult:
        """K-nearest neighbors across all embeddings."""
        neighbors = []
        for emb_key, emb in self.embeddings.items():
            # Pad or truncate query vector to match embedding dimension
            qv = query_vector[:emb.dimension]
            if len(qv) < emb.dimension:
                qv = qv + [0.0] * (emb.dimension - len(qv))
            score = _cosine_similarity(qv, emb.vector)
            neighbors.append({
                "entity_id": emb.entity_id,
                "entity_type": emb.entity_type,
                "score": round(score, 4),
            })

        neighbors.sort(key=lambda x: x["score"], reverse=True)
        return KNNResult(query_id="query", k=k, neighbors=neighbors[:k])


REPO_CLASS = EmbeddingRepository
repo = EmbeddingRepository(seed=True)
