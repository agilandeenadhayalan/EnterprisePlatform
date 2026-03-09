"""
Reporting Service — FastAPI application.

Scheduled and ad-hoc report generation for the Smart Mobility Platform.
Supports multiple report types and output formats.

ROUTES:
  GET    /reports            — List all reports (supports ?type= and ?status= filters)
  POST   /reports/generate   — Generate a new report
  GET    /reports/types      — List available report types
  GET    /reports/{id}       — Get report details and results
  DELETE /reports/{id}       — Delete a report
  GET    /health             — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Query

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
    description="Scheduled and ad-hoc report generation for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/reports", response_model=schemas.ReportListResponse)
async def list_reports(
    type: Optional[str] = Query(default=None, alias="type", description="Filter by report type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all reports, optionally filtered by type or status."""
    reports = repository.repo.list_reports(report_type=type, status=status)
    return schemas.ReportListResponse(
        reports=[schemas.ReportResponse(**r.to_dict()) for r in reports],
        total=len(reports),
    )


@app.post("/reports/generate", response_model=schemas.ReportResponse, status_code=201)
async def generate_report(body: schemas.ReportGenerateRequest):
    """Generate a new report of the specified type."""
    # Validate report type exists
    report_type = repository.repo.get_report_type(body.report_type)
    if not report_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown report type: '{body.report_type}'. Use GET /reports/types to see available types.",
        )

    # Validate required parameters
    missing = [p for p in report_type.required_params if p not in body.parameters]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required parameters for {body.report_type}: {missing}",
        )

    # Validate format
    if body.format not in report_type.supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Format '{body.format}' not supported for {body.report_type}. "
                   f"Supported: {report_type.supported_formats}",
        )

    report = repository.repo.create_report(
        report_type=body.report_type,
        parameters=body.parameters,
        format=body.format,
    )
    return schemas.ReportResponse(**report.to_dict())


@app.get("/reports/types", response_model=schemas.ReportTypeListResponse)
async def list_report_types():
    """List all available report types with their parameters and supported formats."""
    types = repository.repo.get_report_types()
    return schemas.ReportTypeListResponse(
        report_types=[schemas.ReportTypeResponse(**t.to_dict()) for t in types],
        total=len(types),
    )


@app.get("/reports/{report_id}", response_model=schemas.ReportResponse)
async def get_report(report_id: str):
    """Get report details and results by ID."""
    report = repository.repo.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return schemas.ReportResponse(**report.to_dict())


@app.delete("/reports/{report_id}", status_code=204)
async def delete_report(report_id: str):
    """Delete a report."""
    deleted = repository.repo.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
