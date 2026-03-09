"""
SLO Tracker Service — FastAPI application.

SLO definition, error budget tracking, and burn rate alerting
for the observability platform.

ROUTES:
  GET  /slos                  — List SLO definitions
  POST /slos                  — Create SLO
  GET  /slos/{id}             — Get SLO
  GET  /slos/{id}/budget      — Error budget details
  GET  /slos/{id}/history     — Compliance history
  POST /slos/{id}/record      — Record measurement
  GET  /slos/{id}/burn-rate   — Burn rate alerts
  GET  /slos/stats            — SLO statistics
  GET  /health                — Health check (provided by create_app)
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
    description="SLO definition, error budget tracking, and burn rate alerting for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/slos/stats", response_model=schemas.SloStatsResponse)
async def slo_stats():
    """Get SLO statistics."""
    stats = repository.repo.get_stats()
    return schemas.SloStatsResponse(**stats)


@app.get("/slos", response_model=schemas.SloDefinitionListResponse)
async def list_slos():
    """List all SLO definitions."""
    slos = repository.repo.list_slos()
    return schemas.SloDefinitionListResponse(
        slos=[schemas.SloDefinitionResponse(**s.to_dict()) for s in slos],
        total=len(slos),
    )


@app.post("/slos", response_model=schemas.SloDefinitionResponse, status_code=201)
async def create_slo(req: schemas.SloCreateRequest):
    """Create a new SLO definition."""
    existing = repository.repo.find_slo_by_service_and_type(req.service_name, req.slo_type)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"SLO for {req.service_name} ({req.slo_type}) already exists",
        )
    slo = repository.repo.create_slo(req.model_dump())
    return schemas.SloDefinitionResponse(**slo.to_dict())


@app.get("/slos/{slo_id}", response_model=schemas.SloDefinitionResponse)
async def get_slo(slo_id: str):
    """Get a single SLO definition by ID."""
    slo = repository.repo.get_slo(slo_id)
    if not slo:
        raise HTTPException(status_code=404, detail=f"SLO '{slo_id}' not found")
    return schemas.SloDefinitionResponse(**slo.to_dict())


@app.get("/slos/{slo_id}/budget", response_model=schemas.ErrorBudgetResponse)
async def error_budget(slo_id: str):
    """Get error budget for an SLO."""
    budget = repository.repo.get_error_budget(slo_id)
    if not budget:
        raise HTTPException(status_code=404, detail=f"SLO '{slo_id}' not found")
    return schemas.ErrorBudgetResponse(**budget)


@app.get("/slos/{slo_id}/history", response_model=schemas.SloRecordListResponse)
async def compliance_history(slo_id: str):
    """Get compliance history for an SLO."""
    records = repository.repo.list_records_for_slo(slo_id)
    return schemas.SloRecordListResponse(
        records=[schemas.SloRecordResponse(**r.to_dict()) for r in records],
        total=len(records),
    )


@app.post("/slos/{slo_id}/record", response_model=schemas.SloRecordResponse, status_code=201)
async def record_measurement(slo_id: str, req: schemas.SloRecordCreateRequest):
    """Record a measurement for an SLO."""
    record = repository.repo.record_measurement(slo_id, req.good_events, req.total_events)
    if not record:
        raise HTTPException(status_code=404, detail=f"SLO '{slo_id}' not found")
    return schemas.SloRecordResponse(**record.to_dict())


@app.get("/slos/{slo_id}/burn-rate", response_model=schemas.BurnRateAlertListResponse)
async def burn_rate_alerts(slo_id: str):
    """Get burn rate alerts for an SLO."""
    alerts = repository.repo.list_burn_rate_alerts(slo_id)
    return schemas.BurnRateAlertListResponse(
        alerts=[schemas.BurnRateAlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
    )
