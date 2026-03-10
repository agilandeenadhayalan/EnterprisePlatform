"""
Conflict Resolver Service — FastAPI application.

CRDT merge operations, conflict detection, and resolution strategies.

ROUTES:
  POST   /conflicts/detect      — Detect conflicts between two versions
  POST   /conflicts/resolve     — Resolve conflict using strategy
  GET    /conflicts              — List conflict records
  GET    /conflicts/{id}        — Get conflict details
  POST   /conflicts/merge       — CRDT merge operation
  GET    /conflicts/strategies  — List available strategies
  GET    /conflicts/stats       — Resolution statistics
  GET    /health                — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

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
    description="CRDT merge operations, conflict detection, and resolution strategies",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/conflicts/detect", response_model=schemas.ConflictResponse, status_code=201)
async def detect_conflict(body: schemas.DetectRequest):
    """Detect conflicts between two versions."""
    conflict = repository.repo.detect_conflict(
        entity_id=body.entity_id,
        version_a=body.version_a,
        version_b=body.version_b,
    )
    return schemas.ConflictResponse(**conflict.to_dict())


@app.post("/conflicts/resolve", response_model=schemas.ConflictResponse)
async def resolve_conflict(body: schemas.ResolveRequest):
    """Resolve conflict using strategy."""
    valid_strategies = ["lww", "merge", "manual", "crdt"]
    if body.strategy not in valid_strategies:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy '{body.strategy}'. Must be one of: {', '.join(valid_strategies)}",
        )
    conflict = repository.repo.resolve_conflict(
        conflict_id=body.conflict_id,
        strategy=body.strategy,
        manual_value=body.manual_value,
    )
    if not conflict:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Conflict '{body.conflict_id}' not found")
    return schemas.ConflictResponse(**conflict.to_dict())


@app.get("/conflicts/strategies", response_model=list[schemas.StrategyResponse])
async def list_strategies():
    """List available resolution strategies."""
    return repository.repo.get_strategies()


@app.get("/conflicts/stats", response_model=schemas.ConflictStatsResponse)
async def get_stats():
    """Get conflict resolution statistics."""
    return repository.repo.get_stats()


@app.post("/conflicts/merge", response_model=schemas.MergeResultResponse)
async def crdt_merge(body: schemas.MergeRequest):
    """Perform a CRDT merge operation."""
    valid_types = ["counter", "set", "register"]
    if body.merge_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid merge type '{body.merge_type}'. Must be one of: {', '.join(valid_types)}",
        )
    result = repository.repo.crdt_merge(
        merge_type=body.merge_type,
        state_a=body.state_a,
        state_b=body.state_b,
    )
    return schemas.MergeResultResponse(**result.to_dict())


@app.get("/conflicts", response_model=list[schemas.ConflictResponse])
async def list_conflicts():
    """List all conflict records."""
    conflicts = repository.repo.list_conflicts()
    return [schemas.ConflictResponse(**c.to_dict()) for c in conflicts]


@app.get("/conflicts/{conflict_id}", response_model=schemas.ConflictResponse)
async def get_conflict(conflict_id: str):
    """Get conflict details."""
    conflict = repository.repo.get_conflict(conflict_id)
    if not conflict:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found")
    return schemas.ConflictResponse(**conflict.to_dict())
