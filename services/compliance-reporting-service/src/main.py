"""
Compliance Reporting Service — FastAPI application.

Generates compliance reports against regulatory frameworks (SOC2, ISO27001, GDPR, HIPAA).

ROUTES:
  GET    /compliance/reports                   — List reports (filter by framework, status)
  POST   /compliance/reports                   — Generate a new compliance report
  GET    /compliance/reports/{id}              — Get report details
  PATCH  /compliance/reports/{id}              — Update report findings/status
  DELETE /compliance/reports/{id}              — Delete report
  GET    /compliance/frameworks                — List supported frameworks
  POST   /compliance/reports/{id}/findings     — Add finding to report
  GET    /health                               — Health check (provided by create_app)
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
    description="Generates compliance reports against regulatory frameworks",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/compliance/reports", response_model=list[schemas.ReportResponse])
async def list_reports(framework: str | None = None, status: str | None = None):
    """List all compliance reports."""
    reports = repository.repo.list_reports(framework=framework, status=status)
    return [schemas.ReportResponse(**r.to_dict()) for r in reports]


@app.post("/compliance/reports", response_model=schemas.ReportResponse, status_code=201)
async def create_report(body: schemas.ReportCreate):
    """Generate a new compliance report."""
    valid_frameworks = [f["name"] for f in repository.FRAMEWORKS]
    if body.framework not in valid_frameworks:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework '{body.framework}'. Must be one of: {', '.join(valid_frameworks)}",
        )

    report = repository.repo.create_report(
        report_type=body.report_type,
        framework=body.framework,
        generated_by=body.generated_by,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    return schemas.ReportResponse(**report.to_dict())


@app.get("/compliance/reports/{report_id}", response_model=schemas.ReportResponse)
async def get_report(report_id: str):
    """Get a compliance report by ID."""
    report = repository.repo.get_report(report_id)
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return schemas.ReportResponse(**report.to_dict())


@app.patch("/compliance/reports/{report_id}", response_model=schemas.ReportResponse)
async def update_report(report_id: str, body: schemas.ReportUpdate):
    """Update a compliance report."""
    update_fields = body.model_dump(exclude_unset=True)
    report = repository.repo.update_report(report_id, **update_fields)
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return schemas.ReportResponse(**report.to_dict())


@app.delete("/compliance/reports/{report_id}", status_code=204)
async def delete_report(report_id: str):
    """Delete a compliance report."""
    deleted = repository.repo.delete_report(report_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")


@app.get("/compliance/frameworks", response_model=list[schemas.FrameworkResponse])
async def list_frameworks():
    """List all supported compliance frameworks."""
    frameworks = repository.repo.get_frameworks()
    return [schemas.FrameworkResponse(**f) for f in frameworks]


@app.post("/compliance/reports/{report_id}/findings", response_model=schemas.FindingResponse, status_code=201)
async def add_finding(report_id: str, body: schemas.FindingCreate):
    """Add a finding to a compliance report."""
    finding = repository.repo.add_finding(
        report_id=report_id,
        category=body.category,
        description=body.description,
        severity=body.severity,
        remediation=body.remediation,
        status=body.status,
    )
    if not finding:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return schemas.FindingResponse(**finding)
