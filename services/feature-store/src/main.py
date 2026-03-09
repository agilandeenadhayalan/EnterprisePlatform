"""
Feature Store — FastAPI application.

Online/offline feature registry and serving for the ML platform.
Provides CRUD for feature definitions, online/offline feature retrieval,
feature value ingestion, and statistics.

ROUTES:
  GET  /features/definitions              — List all feature definitions
  POST /features/definitions              — Register a new feature definition
  GET  /features/definitions/{name}       — Get feature definition details
  POST /features/online                   — Get online features for entity
  POST /features/offline                  — Get offline features for training
  POST /features/ingest                   — Ingest computed feature values
  GET  /features/stats                    — Feature statistics
  GET  /health                            — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

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
    description="Online/offline feature registry and serving for the ML platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/features/definitions", response_model=schemas.FeatureDefinitionListResponse)
async def list_definitions(
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
):
    """List all registered feature definitions."""
    defs = repository.repo.list_definitions()
    if entity_type:
        defs = [d for d in defs if d.entity_type == entity_type]
    if is_active is not None:
        defs = [d for d in defs if d.is_active == is_active]
    return schemas.FeatureDefinitionListResponse(
        definitions=[schemas.FeatureDefinitionResponse(**d.to_dict()) for d in defs],
        total=len(defs),
    )


@app.post("/features/definitions", response_model=schemas.FeatureDefinitionResponse, status_code=201)
async def create_definition(req: schemas.FeatureDefinitionCreateRequest):
    """Register a new feature definition."""
    existing = repository.repo.get_definition(req.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Feature '{req.name}' already exists")
    fd = repository.repo.create_definition(req.model_dump())
    return schemas.FeatureDefinitionResponse(**fd.to_dict())


@app.get("/features/definitions/{name}", response_model=schemas.FeatureDefinitionResponse)
async def get_definition(name: str):
    """Get a single feature definition by name."""
    fd = repository.repo.get_definition(name)
    if not fd:
        raise HTTPException(status_code=404, detail=f"Feature '{name}' not found")
    return schemas.FeatureDefinitionResponse(**fd.to_dict())


@app.post("/features/online", response_model=schemas.FeatureVectorResponse)
async def get_online_features(req: schemas.OnlineFeatureRequest):
    """Get online feature values for a single entity."""
    vec = repository.repo.get_online_features(req.entity_id, req.feature_names)
    return schemas.FeatureVectorResponse(**vec.to_dict())


@app.post("/features/offline", response_model=schemas.OfflineFeatureResponse)
async def get_offline_features(req: schemas.OfflineFeatureRequest):
    """Get offline feature values for multiple entities (training)."""
    vectors = repository.repo.get_offline_features(req.entity_ids, req.feature_names)
    return schemas.OfflineFeatureResponse(
        vectors=[schemas.FeatureVectorResponse(**v.to_dict()) for v in vectors],
        total=len(vectors),
    )


@app.post("/features/ingest", response_model=schemas.IngestResponse)
async def ingest_features(req: schemas.IngestRequest):
    """Ingest a computed feature value."""
    repository.repo.ingest_value(
        entity_id=req.entity_id,
        feature_name=req.feature_name,
        value=req.value,
        timestamp=req.timestamp,
    )
    return schemas.IngestResponse(ingested=1, message="Feature value ingested successfully")


@app.get("/features/stats", response_model=schemas.FeatureStatsResponse)
async def feature_stats():
    """Get feature store statistics."""
    stats = repository.repo.get_stats()
    return schemas.FeatureStatsResponse(**stats)
