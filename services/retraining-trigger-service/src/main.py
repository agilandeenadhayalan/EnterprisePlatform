"""
Retraining Trigger Service — FastAPI application.

Drift-based automatic retraining triggers. Monitors model performance
and data drift to decide when models need retraining.

ROUTES:
  POST /triggers              — Create a retraining trigger rule
  GET  /triggers              — List trigger rules
  GET  /triggers/{id}         — Get trigger details
  POST /triggers/evaluate     — Evaluate all triggers against current metrics
  GET  /triggers/history      — Retraining trigger history
  POST /triggers/{id}/fire    — Manually fire a trigger
  GET  /health                — Health check (provided by create_app)
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
    description="Drift-based automatic retraining triggers for ML models",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/triggers", response_model=schemas.TriggerResponse, status_code=201)
async def create_trigger(body: schemas.TriggerCreateRequest):
    """Create a new retraining trigger rule."""
    trigger = repository.repo.create_trigger(
        model_name=body.model_name,
        trigger_type=body.trigger_type,
        condition=body.condition,
        threshold=body.threshold,
        cooldown_hours=body.cooldown_hours,
        is_active=body.is_active,
    )
    return schemas.TriggerResponse(**trigger.to_dict())


@app.get("/triggers", response_model=schemas.TriggerListResponse)
async def list_triggers():
    """List all retraining trigger rules."""
    triggers = repository.repo.list_triggers()
    return schemas.TriggerListResponse(
        triggers=[schemas.TriggerResponse(**t.to_dict()) for t in triggers],
        total=len(triggers),
    )


@app.get("/triggers/history", response_model=schemas.TriggerHistoryListResponse)
async def get_trigger_history():
    """Get the history of all trigger firings."""
    history = repository.repo.get_history()
    return schemas.TriggerHistoryListResponse(
        history=[schemas.TriggerHistoryResponse(**h.to_dict()) for h in history],
        total=len(history),
    )


@app.post("/triggers/evaluate", response_model=schemas.EvaluateAllResponse)
async def evaluate_triggers():
    """Evaluate all active triggers against current metrics."""
    evaluations = repository.repo.evaluate_all()
    fired_count = sum(1 for e in evaluations if e.fired)
    return schemas.EvaluateAllResponse(
        evaluations=[schemas.TriggerEvaluationResponse(**e.to_dict()) for e in evaluations],
        total=len(evaluations),
        fired_count=fired_count,
    )


@app.get("/triggers/{trigger_id}", response_model=schemas.TriggerResponse)
async def get_trigger(trigger_id: str):
    """Get details for a specific trigger rule."""
    trigger = repository.repo.get_trigger(trigger_id)
    if trigger is None:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    return schemas.TriggerResponse(**trigger.to_dict())


@app.post("/triggers/{trigger_id}/fire", response_model=schemas.TriggerHistoryResponse)
async def fire_trigger(trigger_id: str):
    """Manually fire a trigger."""
    entry = repository.repo.fire_trigger(trigger_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    return schemas.TriggerHistoryResponse(**entry.to_dict())
