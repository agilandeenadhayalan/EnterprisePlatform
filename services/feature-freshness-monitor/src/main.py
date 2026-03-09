"""
Feature Freshness Monitor — FastAPI application.

Feature staleness detection and alerting. Monitors feature freshness
against SLA targets and generates violations when features become stale.

ROUTES:
  GET  /freshness/status     — Overall freshness dashboard
  GET  /freshness/features   — Per-feature freshness status
  GET  /freshness/violations — Features violating freshness SLA
  POST /freshness/check      — Trigger a freshness check run
  POST /freshness/sla        — Set/update freshness SLA
  GET  /health               — Health check (provided by create_app)
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
    description="Feature staleness detection and alerting for the ML platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/freshness/status", response_model=schemas.DashboardResponse)
async def freshness_dashboard():
    """Overall freshness dashboard with summary metrics."""
    dashboard = repository.repo.get_dashboard()
    return schemas.DashboardResponse(**dashboard)


@app.get("/freshness/features", response_model=schemas.FreshnessStatusListResponse)
async def feature_freshness(
    is_fresh: Optional[bool] = Query(default=None, description="Filter by freshness status"),
):
    """Per-feature freshness status."""
    statuses = repository.repo.get_all_statuses()
    if is_fresh is not None:
        statuses = [s for s in statuses if s.is_fresh == is_fresh]
    fresh_count = sum(1 for s in statuses if s.is_fresh)
    stale_count = len(statuses) - fresh_count
    return schemas.FreshnessStatusListResponse(
        features=[schemas.FreshnessStatusResponse(**s.to_dict()) for s in statuses],
        total=len(statuses),
        fresh_count=fresh_count,
        stale_count=stale_count,
    )


@app.get("/freshness/violations", response_model=schemas.ViolationListResponse)
async def freshness_violations(
    severity: Optional[str] = Query(default=None, description="Filter by severity (critical/warning)"),
):
    """Features currently violating their freshness SLA."""
    violations = repository.repo.get_violations()
    if severity:
        violations = [v for v in violations if v.severity == severity]
    return schemas.ViolationListResponse(
        violations=[schemas.FreshnessViolationResponse(**v.to_dict()) for v in violations],
        total=len(violations),
    )


@app.post("/freshness/check", response_model=schemas.CheckRunResponse)
async def run_freshness_check():
    """Trigger a freshness check run across all features."""
    result = repository.repo.run_check()
    return schemas.CheckRunResponse(**result)


@app.post("/freshness/sla", response_model=schemas.SlaUpdateResponse)
async def set_sla(req: schemas.SlaUpdateRequest):
    """Set or update the freshness SLA for a feature."""
    result = repository.repo.set_sla(req.feature_name, req.sla_seconds)
    return schemas.SlaUpdateResponse(**result)
