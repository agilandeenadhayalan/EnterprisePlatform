"""
Health Check Service — FastAPI application.

Service health probing, dependency mapping, and dashboard for the
observability platform.

ROUTES:
  GET  /health-checks/probes             — List probes
  POST /health-checks/probes             — Register probe
  GET  /health-checks/probes/{probe_id}  — Get probe
  POST /health-checks/run/{probe_id}     — Run health check
  GET  /health-checks/results            — List results
  GET  /health-checks/dashboard          — Aggregate dashboard
  GET  /health-checks/dependencies       — Dependency graph
  GET  /health-checks/stats              — Health check statistics
  GET  /health                           — Health check (provided by create_app)
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
    description="Service health probing, dependency mapping, and dashboard for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/health-checks/probes", response_model=schemas.ServiceProbeListResponse)
async def list_probes():
    """List all registered health check probes."""
    probes = repository.repo.list_probes()
    return schemas.ServiceProbeListResponse(
        probes=[schemas.ServiceProbeResponse(**p.to_dict()) for p in probes],
        total=len(probes),
    )


@app.post("/health-checks/probes", response_model=schemas.ServiceProbeResponse, status_code=201)
async def create_probe(req: schemas.ServiceProbeCreateRequest):
    """Register a new health check probe."""
    probe = repository.repo.create_probe(req.model_dump())
    return schemas.ServiceProbeResponse(**probe.to_dict())


@app.get("/health-checks/probes/{probe_id}", response_model=schemas.ServiceProbeResponse)
async def get_probe(probe_id: str):
    """Get a single probe by ID."""
    probe = repository.repo.get_probe(probe_id)
    if not probe:
        raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")
    return schemas.ServiceProbeResponse(**probe.to_dict())


@app.post("/health-checks/run/{probe_id}", response_model=schemas.HealthCheckResultResponse)
async def run_check(probe_id: str):
    """Run a health check for a probe (simulated)."""
    result = repository.repo.run_check(probe_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")
    return schemas.HealthCheckResultResponse(**result.to_dict())


@app.get("/health-checks/results", response_model=schemas.HealthCheckResultListResponse)
async def list_results(
    service_name: Optional[str] = Query(default=None, description="Filter by service name"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List health check results."""
    results = repository.repo.list_results()
    if service_name:
        results = [r for r in results if r.service_name == service_name]
    if status:
        results = [r for r in results if r.status == status]
    return schemas.HealthCheckResultListResponse(
        results=[schemas.HealthCheckResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/health-checks/dashboard", response_model=schemas.DashboardResponse)
async def dashboard():
    """Aggregate health dashboard with latest status per service."""
    data = repository.repo.get_dashboard()
    return schemas.DashboardResponse(
        services=[schemas.ServiceStatusSummary(**s) for s in data["services"]],
        overall_status=data["overall_status"],
    )


@app.get("/health-checks/dependencies", response_model=schemas.DependencyGraphResponse)
async def dependencies():
    """Service dependency graph."""
    deps = repository.repo.get_dependencies()
    return schemas.DependencyGraphResponse(
        nodes=[schemas.DependencyNodeResponse(**d.to_dict()) for d in deps],
        total=len(deps),
    )


@app.get("/health-checks/stats", response_model=schemas.HealthCheckStatsResponse)
async def stats():
    """Get health check statistics."""
    data = repository.repo.get_stats()
    return schemas.HealthCheckStatsResponse(**data)
