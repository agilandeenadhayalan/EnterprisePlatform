"""
Safety Service — FastAPI application.

Driver and rider safety scoring and alert management.

ROUTES:
  GET    /safety/scores                                  — List safety scores
  POST   /safety/scores                                  — Calculate/record safety score
  GET    /safety/scores/{entity_type}/{entity_id}        — Get safety score
  GET    /safety/alerts                                  — List safety alerts
  POST   /safety/alerts                                  — Create safety alert
  PATCH  /safety/alerts/{id}                             — Update alert status
  GET    /safety/scores/{entity_type}/{entity_id}/history — Score history
  GET    /health                                          — Health check (provided by create_app)
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
from models import EntityType


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Driver and rider safety scoring and alerts",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/safety/scores", response_model=list[schemas.SafetyScoreResponse])
async def list_scores():
    """List all safety scores."""
    scores = repository.repo.list_scores()
    return [schemas.SafetyScoreResponse(**s.to_dict()) for s in scores]


@app.post("/safety/scores", response_model=schemas.SafetyScoreResponse, status_code=201)
async def create_score(body: schemas.SafetyScoreCreate):
    """Calculate/record a safety score."""
    valid_types = [t.value for t in EntityType]
    if body.entity_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{body.entity_type}'. Must be one of: {', '.join(valid_types)}",
        )

    score = repository.repo.create_score(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        score=body.score,
        factors=body.factors,
    )
    return schemas.SafetyScoreResponse(**score.to_dict())


@app.get("/safety/scores/{entity_type}/{entity_id}", response_model=schemas.SafetyScoreResponse)
async def get_score(entity_type: str, entity_id: str):
    """Get safety score for an entity."""
    score = repository.repo.get_score(entity_type, entity_id)
    if not score:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Score for {entity_type}/{entity_id} not found")
    return schemas.SafetyScoreResponse(**score.to_dict())


@app.get("/safety/alerts", response_model=list[schemas.SafetyAlertResponse])
async def list_alerts():
    """List all safety alerts."""
    alerts = repository.repo.list_alerts()
    return [schemas.SafetyAlertResponse(**a.to_dict()) for a in alerts]


@app.post("/safety/alerts", response_model=schemas.SafetyAlertResponse, status_code=201)
async def create_alert(body: schemas.AlertCreate):
    """Create a safety alert."""
    valid_types = [t.value for t in EntityType]
    if body.entity_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{body.entity_type}'. Must be one of: {', '.join(valid_types)}",
        )

    alert = repository.repo.create_alert(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        alert_type=body.alert_type,
        severity=body.severity,
        message=body.message,
    )
    return schemas.SafetyAlertResponse(**alert.to_dict())


@app.patch("/safety/alerts/{alert_id}", response_model=schemas.SafetyAlertResponse)
async def update_alert(alert_id: str, body: schemas.AlertUpdate):
    """Update a safety alert."""
    update_fields = body.model_dump(exclude_unset=True)
    alert = repository.repo.update_alert(alert_id, **update_fields)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.SafetyAlertResponse(**alert.to_dict())


@app.get("/safety/scores/{entity_type}/{entity_id}/history", response_model=list[schemas.SafetyScoreResponse])
async def get_score_history(entity_type: str, entity_id: str):
    """Get score history for an entity."""
    history = repository.repo.get_score_history(entity_type, entity_id)
    return [schemas.SafetyScoreResponse(**s.to_dict()) for s in history]
