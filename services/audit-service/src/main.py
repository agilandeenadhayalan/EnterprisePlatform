"""
Audit Service — FastAPI application.

Immutable audit trail and event logging with hash chain tamper detection.

ROUTES:
  GET    /audit/logs                              — Query audit logs
  POST   /audit/logs                              — Record an audit event
  GET    /audit/logs/{id}                         — Get specific log entry
  GET    /audit/logs/entity/{entity_type}/{id}    — Logs for entity
  GET    /audit/logs/actor/{actor}                — Logs by actor
  POST   /audit/logs/search                       — Advanced search
  GET    /audit/stats                             — Audit statistics
  GET    /health                                  — Health check (provided by create_app)
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
    description="Immutable audit trail and event logging",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/audit/logs", response_model=list[schemas.AuditLogResponse])
async def list_logs(
    entity_type: str | None = None,
    actor: str | None = None,
    action: str | None = None,
):
    """Query audit logs with optional filters."""
    logs = repository.repo.list_logs(
        entity_type=entity_type,
        actor=actor,
        action=action,
    )
    return [schemas.AuditLogResponse(**l.to_dict()) for l in logs]


@app.post("/audit/logs", response_model=schemas.AuditLogResponse, status_code=201)
async def create_log(body: schemas.AuditLogCreate):
    """Record an audit event."""
    valid_actions = ["create", "read", "update", "delete", "login", "export", "approve"]
    if body.action not in valid_actions:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{body.action}'. Must be one of: {', '.join(valid_actions)}",
        )
    log = repository.repo.create_log(
        action=body.action,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        actor=body.actor,
        details=body.details,
        region=body.region,
        ip_address=body.ip_address,
    )
    return schemas.AuditLogResponse(**log.to_dict())


@app.get("/audit/stats", response_model=schemas.AuditStatsResponse)
async def get_stats():
    """Audit statistics."""
    return repository.repo.get_stats()


@app.post("/audit/logs/search", response_model=list[schemas.AuditLogResponse])
async def search_logs(body: schemas.AuditSearchRequest):
    """Advanced search with multiple filters."""
    logs = repository.repo.search_logs(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        actor=body.actor,
        action=body.action,
        region=body.region,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return [schemas.AuditLogResponse(**l.to_dict()) for l in logs]


@app.get("/audit/logs/entity/{entity_type}/{entity_id}", response_model=list[schemas.AuditLogResponse])
async def logs_for_entity(entity_type: str, entity_id: str):
    """Get logs for a specific entity."""
    logs = repository.repo.logs_for_entity(entity_type, entity_id)
    return [schemas.AuditLogResponse(**l.to_dict()) for l in logs]


@app.get("/audit/logs/actor/{actor}", response_model=list[schemas.AuditLogResponse])
async def logs_by_actor(actor: str):
    """Get logs by actor."""
    logs = repository.repo.logs_by_actor(actor)
    return [schemas.AuditLogResponse(**l.to_dict()) for l in logs]


@app.get("/audit/logs/{log_id}", response_model=schemas.AuditLogResponse)
async def get_log(log_id: str):
    """Get a specific audit log entry."""
    log = repository.repo.get_log(log_id)
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Audit log '{log_id}' not found")
    return schemas.AuditLogResponse(**log.to_dict())
