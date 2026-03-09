"""
Pydantic response schemas for the Embedding service.
"""

from typing import Any, Dict, List
from pydantic import BaseModel


# ── Request schemas ──

class EmbeddingComputeRequest(BaseModel):
    entity_type: str
    entity_id: str
    features: Dict[str, float]


class SimilarityRequest(BaseModel):
    entity_type: str
    entity_id: str
    k: int = 5


class BatchEmbeddingRequest(BaseModel):
    entities: List[EmbeddingComputeRequest]


class KNNRequest(BaseModel):
    query_vector: List[float]
    k: int = 5


# ── Response schemas ──

class EmbeddingResponse(BaseModel):
    entity_id: str
    entity_type: str
    vector: List[float]
    dimension: int
    computed_at: str


class SimilarEntityResult(BaseModel):
    entity_id: str
    score: float


class SimilarityResponse(BaseModel):
    query_id: str
    results: List[SimilarEntityResult]


class BatchEmbeddingResponse(BaseModel):
    computed: int
    embeddings: List[EmbeddingResponse]


class KNNNeighbor(BaseModel):
    entity_id: str
    entity_type: str
    score: float


class KNNResponse(BaseModel):
    query_id: str
    k: int
    neighbors: List[KNNNeighbor]
