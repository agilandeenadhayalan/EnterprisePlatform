"""
Model Registry Service — FastAPI application.

MLflow model registry proxy and versioning. Manages model registration,
versioning, stage transitions (none -> staging -> production -> archived),
and production version retrieval.

ROUTES:
  POST /registry/models                           — Register a model
  GET  /registry/models                           — List registered models
  GET  /registry/models/{name}                    — Model details + versions
  GET  /registry/models/{name}/versions            — List all versions
  POST /registry/models/{name}/versions            — Create new version
  POST /registry/models/{name}/versions/{v}/stage  — Transition stage
  GET  /registry/models/{name}/production          — Get production version
  GET  /health                                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query

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
    description="MLflow model registry proxy and versioning",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/registry/models", response_model=schemas.RegisteredModelResponse, status_code=201)
async def register_model(request: schemas.RegisterModelRequest):
    """Register a new model."""
    try:
        model = repository.repo.register_model(
            name=request.name,
            description=request.description,
            model_type=request.model_type,
            task_type=request.task_type,
        )
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(exc))
    return schemas.RegisteredModelResponse(**model.to_dict())


@app.get("/registry/models", response_model=schemas.RegisteredModelListResponse)
async def list_models():
    """List all registered models."""
    models = repository.repo.list_models()
    return schemas.RegisteredModelListResponse(
        models=[schemas.RegisteredModelResponse(**m.to_dict()) for m in models],
        total=len(models),
    )


@app.get("/registry/models/{name}", response_model=schemas.RegisteredModelDetailResponse)
async def get_model(name: str):
    """Get model details including all versions."""
    model = repository.repo.get_model(name)
    if model is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    versions = repository.repo.list_versions(name)
    model_dict = model.to_dict()
    model_dict["versions"] = [schemas.ModelVersionResponse(**v.to_dict()) for v in versions]
    return schemas.RegisteredModelDetailResponse(**model_dict)


@app.get("/registry/models/{name}/versions", response_model=schemas.ModelVersionListResponse)
async def list_versions(name: str):
    """List all versions of a model."""
    model = repository.repo.get_model(name)
    if model is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    versions = repository.repo.list_versions(name)
    return schemas.ModelVersionListResponse(
        versions=[schemas.ModelVersionResponse(**v.to_dict()) for v in versions],
        total=len(versions),
    )


@app.post("/registry/models/{name}/versions", response_model=schemas.ModelVersionResponse, status_code=201)
async def create_version(name: str, request: schemas.CreateVersionRequest):
    """Create a new version for a model."""
    version = repository.repo.create_version(
        model_name=name,
        run_id=request.run_id,
        metrics=request.metrics,
        hyperparameters=request.hyperparameters,
    )
    if version is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return schemas.ModelVersionResponse(**version.to_dict())


@app.post("/registry/models/{name}/versions/{version}/stage", response_model=schemas.StageTransitionResponse)
async def transition_stage(name: str, version: int, request: schemas.StageTransitionRequest):
    """Transition a model version to a new stage."""
    result = repository.repo.transition_stage(
        model_name=name,
        version_num=version,
        stage=request.stage,
        reason=request.reason,
    )
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Model '{name}' version {version} not found",
        )
    transition, ver = result
    return schemas.StageTransitionResponse(
        from_stage=transition.from_stage,
        to_stage=transition.to_stage,
        reason=transition.reason,
        version=schemas.ModelVersionResponse(**ver.to_dict()),
    )


@app.get("/registry/models/{name}/production", response_model=schemas.ModelVersionResponse)
async def get_production_version(name: str):
    """Get the production version of a model."""
    version = repository.repo.get_production_version(name)
    if version is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No production version found for model '{name}'",
        )
    return schemas.ModelVersionResponse(**version.to_dict())
