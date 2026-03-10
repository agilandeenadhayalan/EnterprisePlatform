"""
Experiment Analytics Service — FastAPI application.

A/B experiment analysis with statistical significance testing and segment analysis.

ROUTES:
  POST /experiment-analytics/analyze     — Run analysis
  GET  /experiment-analytics/analyses    — List analyses
  GET  /experiment-analytics/analyses/{id} — Get analysis
  POST /experiment-analytics/segment     — Segment analysis
  GET  /experiment-analytics/reports     — List reports
  GET  /experiment-analytics/reports/{id} — Get report
  GET  /experiment-analytics/stats       — Experiment statistics
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
    description="A/B experiment analysis with statistical significance testing and segment analysis",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/experiment-analytics/analyze", response_model=schemas.ExperimentAnalysisResponse, status_code=201)
async def analyze_experiment(req: schemas.AnalyzeExperimentRequest):
    """Run experiment analysis with statistical significance testing."""
    analysis = repository.repo.analyze_experiment(req.model_dump())
    return schemas.ExperimentAnalysisResponse(**analysis.to_dict())


@app.get("/experiment-analytics/analyses", response_model=schemas.ExperimentAnalysisListResponse)
async def list_analyses(
    experiment_id: Optional[str] = Query(default=None, description="Filter by experiment_id"),
):
    """List all experiment analyses."""
    analyses = repository.repo.list_analyses(experiment_id=experiment_id)
    return schemas.ExperimentAnalysisListResponse(
        analyses=[schemas.ExperimentAnalysisResponse(**a.to_dict()) for a in analyses],
        total=len(analyses),
    )


@app.get("/experiment-analytics/analyses/{analysis_id}", response_model=schemas.ExperimentAnalysisResponse)
async def get_analysis(analysis_id: str):
    """Get an experiment analysis by ID."""
    analysis = repository.repo.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
    return schemas.ExperimentAnalysisResponse(**analysis.to_dict())


@app.post("/experiment-analytics/segment", response_model=schemas.SegmentAnalysisResponse)
async def segment_analysis(req: schemas.SegmentAnalysisRequest):
    """Run segment-level analysis."""
    segments = repository.repo.segment_analysis(req.model_dump())
    return schemas.SegmentAnalysisResponse(
        experiment_id=req.experiment_id,
        segments=segments,
    )


@app.get("/experiment-analytics/reports", response_model=schemas.AnalysisReportListResponse)
async def list_reports():
    """List all analysis reports."""
    reports = repository.repo.list_reports()
    return schemas.AnalysisReportListResponse(
        reports=[schemas.AnalysisReportResponse(**r.to_dict()) for r in reports],
        total=len(reports),
    )


@app.get("/experiment-analytics/reports/{report_id}", response_model=schemas.AnalysisReportResponse)
async def get_report(report_id: str):
    """Get an analysis report by ID."""
    report = repository.repo.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return schemas.AnalysisReportResponse(**report.to_dict())


@app.get("/experiment-analytics/stats", response_model=schemas.ExperimentStatsResponse)
async def experiment_stats():
    """Get experiment statistics."""
    stats = repository.repo.get_stats()
    return schemas.ExperimentStatsResponse(**stats)
