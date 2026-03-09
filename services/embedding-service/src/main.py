"""
Embedding Service — FastAPI application.

Feature vector embedding computation, storage, and similarity search.
Supports computing embeddings from feature dicts, cosine similarity
search, batch operations, and k-nearest neighbors.

ROUTES:
  POST /embeddings/compute                    — Compute embedding for entity
  POST /embeddings/similarity                 — Find similar entities
  POST /embeddings/batch                      — Compute embeddings for batch
  GET  /embeddings/{entity_type}/{entity_id}  — Get stored embedding
  POST /embeddings/nearest                    — K-nearest neighbors
  GET  /health                                — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Feature vector embedding computation and similarity search",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/embeddings/compute", response_model=schemas.EmbeddingResponse, status_code=201)
async def compute_embedding(req: schemas.EmbeddingComputeRequest):
    """Compute and store an embedding for an entity."""
    emb = repository.repo.compute_embedding(
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        features=req.features,
    )
    return schemas.EmbeddingResponse(**emb.to_dict())


@app.post("/embeddings/similarity", response_model=schemas.SimilarityResponse)
async def find_similar(req: schemas.SimilarityRequest):
    """Find similar entities by cosine similarity."""
    result = repository.repo.find_similar(
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        k=req.k,
    )
    return schemas.SimilarityResponse(
        query_id=result.query_id,
        results=[schemas.SimilarEntityResult(**r) for r in result.results],
    )


@app.post("/embeddings/batch", response_model=schemas.BatchEmbeddingResponse, status_code=201)
async def batch_compute(req: schemas.BatchEmbeddingRequest):
    """Compute embeddings for a batch of entities."""
    entities = [e.model_dump() for e in req.entities]
    embeddings = repository.repo.compute_batch(entities)
    return schemas.BatchEmbeddingResponse(
        computed=len(embeddings),
        embeddings=[schemas.EmbeddingResponse(**e.to_dict()) for e in embeddings],
    )


@app.get("/embeddings/{entity_type}/{entity_id}", response_model=schemas.EmbeddingResponse)
async def get_embedding(entity_type: str, entity_id: str):
    """Get a stored embedding."""
    emb = repository.repo.get_embedding(entity_type, entity_id)
    if not emb:
        raise HTTPException(status_code=404, detail=f"Embedding for {entity_type}:{entity_id} not found")
    return schemas.EmbeddingResponse(**emb.to_dict())


@app.post("/embeddings/nearest", response_model=schemas.KNNResponse)
async def knn_search(req: schemas.KNNRequest):
    """K-nearest neighbors search against all embeddings."""
    result = repository.repo.knn_search(query_vector=req.query_vector, k=req.k)
    return schemas.KNNResponse(
        query_id=result.query_id,
        k=result.k,
        neighbors=[schemas.KNNNeighbor(**n) for n in result.neighbors],
    )
