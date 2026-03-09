"""
Alerting Service — FastAPI application.

Alert rule management, firing, routing, and event history for the
observability platform.

ROUTES:
  GET  /alerts/rules                — List alert rules
  POST /alerts/rules                — Create alert rule
  GET  /alerts/rules/{rule_id}      — Get alert rule
  POST /alerts/fire                 — Fire alert (creates event)
  POST /alerts/resolve/{event_id}   — Resolve alert event
  POST /alerts/silence/{rule_id}    — Silence alert rule
  POST /alerts/acknowledge/{event_id} — Acknowledge alert event
  GET  /alerts/history              — List alert events
  GET  /alerts/routing              — List routing rules
  GET  /alerts/stats                — Alert statistics
  GET  /health                      — Health check (provided by create_app)
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
    description="Alert rule management, firing, routing, and event history for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/alerts/rules", response_model=schemas.AlertRuleListResponse)
async def list_rules(
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
):
    """List all alert rules."""
    rules = repository.repo.list_rules()
    if severity:
        rules = [r for r in rules if r.severity == severity]
    if is_active is not None:
        rules = [r for r in rules if r.is_active == is_active]
    return schemas.AlertRuleListResponse(
        rules=[schemas.AlertRuleResponse(**r.to_dict()) for r in rules],
        total=len(rules),
    )


@app.post("/alerts/rules", response_model=schemas.AlertRuleResponse, status_code=201)
async def create_rule(req: schemas.AlertRuleCreateRequest):
    """Create a new alert rule."""
    rule = repository.repo.create_rule(req.model_dump())
    return schemas.AlertRuleResponse(**rule.to_dict())


@app.get("/alerts/rules/{rule_id}", response_model=schemas.AlertRuleResponse)
async def get_rule(rule_id: str):
    """Get a single alert rule by ID."""
    rule = repository.repo.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule '{rule_id}' not found")
    return schemas.AlertRuleResponse(**rule.to_dict())


@app.post("/alerts/fire", response_model=schemas.AlertEventResponse, status_code=201)
async def fire_alert(req: schemas.AlertFireRequest):
    """Fire an alert for a rule (creates an AlertEvent with status=firing)."""
    event = repository.repo.fire_alert(req.rule_id, req.message)
    if not event:
        raise HTTPException(status_code=404, detail=f"Alert rule '{req.rule_id}' not found")
    return schemas.AlertEventResponse(**event.to_dict())


@app.post("/alerts/resolve/{event_id}", response_model=schemas.AlertEventResponse)
async def resolve_alert(event_id: str):
    """Resolve a firing alert event."""
    event = repository.repo.resolve_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Alert event '{event_id}' not found")
    return schemas.AlertEventResponse(**event.to_dict())


@app.post("/alerts/silence/{rule_id}", response_model=schemas.AlertRuleResponse)
async def silence_rule(rule_id: str):
    """Silence an alert rule (sets is_active=false)."""
    rule = repository.repo.silence_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule '{rule_id}' not found")
    return schemas.AlertRuleResponse(**rule.to_dict())


@app.post("/alerts/acknowledge/{event_id}", response_model=schemas.AlertEventResponse)
async def acknowledge_alert(event_id: str, req: schemas.AlertAcknowledgeRequest):
    """Acknowledge a firing alert event."""
    event = repository.repo.acknowledge_event(event_id, req.acknowledged_by)
    if not event:
        raise HTTPException(status_code=404, detail=f"Alert event '{event_id}' not found")
    return schemas.AlertEventResponse(**event.to_dict())


@app.get("/alerts/history", response_model=schemas.AlertEventListResponse)
async def alert_history(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
):
    """List alert event history."""
    events = repository.repo.list_events()
    if status:
        events = [e for e in events if e.status == status]
    if severity:
        events = [e for e in events if e.severity == severity]
    return schemas.AlertEventListResponse(
        events=[schemas.AlertEventResponse(**e.to_dict()) for e in events],
        total=len(events),
    )


@app.get("/alerts/routing", response_model=schemas.AlertRoutingListResponse)
async def list_routing():
    """List alert routing rules."""
    rules = repository.repo.list_routing()
    return schemas.AlertRoutingListResponse(
        routing_rules=[schemas.AlertRoutingResponse(**r.to_dict()) for r in rules],
        total=len(rules),
    )


@app.get("/alerts/stats", response_model=schemas.AlertStatsResponse)
async def alert_stats():
    """Get alert statistics."""
    stats = repository.repo.get_stats()
    return schemas.AlertStatsResponse(**stats)
