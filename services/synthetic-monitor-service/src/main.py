"""
Synthetic Monitor Service — FastAPI application.

Synthetic monitoring with HTTP, DNS, and TCP checks
for the observability platform.

ROUTES:
  GET  /synthetic/monitors              — List monitors
  POST /synthetic/monitors              — Create monitor
  GET  /synthetic/monitors/{id}         — Get monitor
  POST /synthetic/monitors/{id}/run     — Run check
  GET  /synthetic/monitors/{id}/results — Results for monitor
  GET  /synthetic/monitors/{id}/uptime  — Uptime report
  GET  /synthetic/stats                 — Synthetic monitoring statistics
  GET  /health                          — Health check (provided by create_app)
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
    description="Synthetic monitoring with HTTP, DNS, and TCP checks for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/synthetic/stats", response_model=schemas.SyntheticStatsResponse)
async def synthetic_stats():
    """Get synthetic monitoring statistics."""
    stats = repository.repo.get_stats()
    return schemas.SyntheticStatsResponse(**stats)


@app.get("/synthetic/monitors", response_model=schemas.SyntheticMonitorListResponse)
async def list_monitors(
    type: Optional[str] = Query(default=None, alias="type", description="Filter by monitor type"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
):
    """List all synthetic monitors."""
    monitors = repository.repo.list_monitors()
    if type:
        monitors = [m for m in monitors if m.monitor_type == type]
    if is_active is not None:
        monitors = [m for m in monitors if m.is_active == is_active]
    return schemas.SyntheticMonitorListResponse(
        monitors=[schemas.SyntheticMonitorResponse(**m.to_dict()) for m in monitors],
        total=len(monitors),
    )


@app.post("/synthetic/monitors", response_model=schemas.SyntheticMonitorResponse, status_code=201)
async def create_monitor(req: schemas.SyntheticMonitorCreateRequest):
    """Create a new synthetic monitor."""
    mon = repository.repo.create_monitor(req.model_dump())
    return schemas.SyntheticMonitorResponse(**mon.to_dict())


@app.get("/synthetic/monitors/{mon_id}", response_model=schemas.SyntheticMonitorResponse)
async def get_monitor(mon_id: str):
    """Get a single monitor by ID."""
    mon = repository.repo.get_monitor(mon_id)
    if not mon:
        raise HTTPException(status_code=404, detail=f"Monitor '{mon_id}' not found")
    return schemas.SyntheticMonitorResponse(**mon.to_dict())


@app.post("/synthetic/monitors/{mon_id}/run", response_model=schemas.SyntheticResultResponse)
async def run_check(mon_id: str):
    """Run a synthetic check for a monitor."""
    result = repository.repo.run_check(mon_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Monitor '{mon_id}' not found")
    return schemas.SyntheticResultResponse(**result.to_dict())


@app.get("/synthetic/monitors/{mon_id}/results", response_model=schemas.SyntheticResultListResponse)
async def monitor_results(mon_id: str):
    """Get results for a specific monitor."""
    results = repository.repo.list_results_for_monitor(mon_id)
    return schemas.SyntheticResultListResponse(
        results=[schemas.SyntheticResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/synthetic/monitors/{mon_id}/uptime", response_model=schemas.UptimeReportResponse)
async def uptime_report(mon_id: str):
    """Get uptime report for a monitor."""
    report = repository.repo.get_uptime_report(mon_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Monitor '{mon_id}' not found")
    return schemas.UptimeReportResponse(**report.to_dict())
