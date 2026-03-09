"""
Deployment Service — FastAPI application.

Deployment management with blue-green, canary, and rolling strategies
for the observability platform.

ROUTES:
  GET  /deployments               — List deployments
  POST /deployments               — Create deployment
  GET  /deployments/{id}          — Get deployment
  POST /deployments/{id}/rollback — Rollback deployment
  GET  /deployments/{id}/history  — Get deployment events
  POST /deployments/{id}/promote  — Promote to next environment
  GET  /deployments/environments  — List environments
  GET  /deployments/stats         — Deployment statistics
  GET  /health                    — Health check (provided by create_app)
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
    description="Deployment management with blue-green, canary, and rolling strategies for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/deployments/environments", response_model=schemas.EnvironmentListResponse)
async def list_environments():
    """List environments with current versions."""
    envs = repository.repo.list_environments()
    return schemas.EnvironmentListResponse(
        environments=[schemas.EnvironmentResponse(**e.to_dict()) for e in envs],
        total=len(envs),
    )


@app.get("/deployments/stats", response_model=schemas.DeploymentStatsResponse)
async def deployment_stats():
    """Get deployment statistics."""
    stats = repository.repo.get_stats()
    return schemas.DeploymentStatsResponse(**stats)


@app.get("/deployments", response_model=schemas.DeploymentListResponse)
async def list_deployments(
    environment: Optional[str] = Query(default=None, description="Filter by environment"),
    strategy: Optional[str] = Query(default=None, description="Filter by strategy"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all deployments."""
    deps = repository.repo.list_deployments()
    if environment:
        deps = [d for d in deps if d.environment == environment]
    if strategy:
        deps = [d for d in deps if d.strategy == strategy]
    if status:
        deps = [d for d in deps if d.status == status]
    return schemas.DeploymentListResponse(
        deployments=[schemas.DeploymentResponse(**d.to_dict()) for d in deps],
        total=len(deps),
    )


@app.post("/deployments", response_model=schemas.DeploymentResponse, status_code=201)
async def create_deployment(req: schemas.DeploymentCreateRequest):
    """Create a new deployment."""
    dep = repository.repo.create_deployment(req.model_dump())
    return schemas.DeploymentResponse(**dep.to_dict())


@app.get("/deployments/{dep_id}", response_model=schemas.DeploymentResponse)
async def get_deployment(dep_id: str):
    """Get a single deployment by ID."""
    dep = repository.repo.get_deployment(dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment '{dep_id}' not found")
    return schemas.DeploymentResponse(**dep.to_dict())


@app.post("/deployments/{dep_id}/rollback", response_model=schemas.DeploymentResponse)
async def rollback_deployment(dep_id: str):
    """Rollback a deployment."""
    dep = repository.repo.get_deployment(dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment '{dep_id}' not found")
    if dep.rolled_back:
        raise HTTPException(status_code=400, detail="Deployment already rolled back")
    result = repository.repo.rollback_deployment(dep_id)
    return schemas.DeploymentResponse(**result.to_dict())


@app.get("/deployments/{dep_id}/history", response_model=schemas.DeploymentEventListResponse)
async def deployment_history(dep_id: str):
    """Get events for a deployment."""
    events = repository.repo.list_events_for_deployment(dep_id)
    return schemas.DeploymentEventListResponse(
        events=[schemas.DeploymentEventResponse(**e.to_dict()) for e in events],
        total=len(events),
    )


@app.post("/deployments/{dep_id}/promote", response_model=schemas.DeploymentResponse, status_code=201)
async def promote_deployment(dep_id: str):
    """Promote a completed deployment to the next environment."""
    dep = repository.repo.get_deployment(dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment '{dep_id}' not found")
    if dep.environment == "production":
        raise HTTPException(status_code=400, detail="Cannot promote from production")
    if dep.status != "completed":
        raise HTTPException(status_code=400, detail="Only completed deployments can be promoted")
    promoted = repository.repo.promote_deployment(dep_id)
    return schemas.DeploymentResponse(**promoted.to_dict())
