"""
Metrics Aggregation Service — FastAPI application.

Metric definitions, data ingestion, querying, and aggregation for the
observability platform.

ROUTES:
  GET  /metrics/definitions            — List metric definitions
  POST /metrics/definitions            — Create metric definition
  GET  /metrics/definitions/{name}     — Get metric definition
  POST /metrics/ingest                 — Ingest data point
  POST /metrics/query                  — Query data points
  POST /metrics/aggregate              — Aggregate metrics
  GET  /metrics/recording-rules        — List recording rules
  POST /metrics/recording-rules        — Create recording rule
  GET  /metrics/stats                  — Metrics statistics
  GET  /health                         — Health check (provided by create_app)
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
    description="Metric definitions, data ingestion, querying, and aggregation for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/metrics/definitions", response_model=schemas.MetricDefinitionListResponse)
async def list_definitions(
    type: Optional[str] = Query(default=None, alias="type", description="Filter by metric type"),
):
    """List all metric definitions."""
    defs = repository.repo.list_definitions()
    if type:
        defs = [d for d in defs if d.metric_type == type]
    return schemas.MetricDefinitionListResponse(
        definitions=[schemas.MetricDefinitionResponse(**d.to_dict()) for d in defs],
        total=len(defs),
    )


@app.post("/metrics/definitions", response_model=schemas.MetricDefinitionResponse, status_code=201)
async def create_definition(req: schemas.MetricDefinitionCreateRequest):
    """Create a new metric definition."""
    existing = repository.repo.get_definition(req.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Metric '{req.name}' already exists")
    md = repository.repo.create_definition(req.model_dump())
    return schemas.MetricDefinitionResponse(**md.to_dict())


@app.get("/metrics/definitions/{name}", response_model=schemas.MetricDefinitionResponse)
async def get_definition(name: str):
    """Get a metric definition by name."""
    md = repository.repo.get_definition(name)
    if not md:
        raise HTTPException(status_code=404, detail=f"Metric '{name}' not found")
    return schemas.MetricDefinitionResponse(**md.to_dict())


@app.post("/metrics/ingest", response_model=schemas.MetricDataPointResponse, status_code=201)
async def ingest_data_point(req: schemas.MetricIngestRequest):
    """Ingest a metric data point."""
    dp = repository.repo.ingest_data_point(req.model_dump())
    return schemas.MetricDataPointResponse(**dp.to_dict())


@app.post("/metrics/query", response_model=schemas.MetricDataPointListResponse)
async def query_metrics(req: schemas.MetricQueryRequest):
    """Query metric data points."""
    points = repository.repo.query(
        metric_name=req.metric_name,
        labels=req.labels,
        time_start=req.time_start,
        time_end=req.time_end,
    )
    return schemas.MetricDataPointListResponse(
        data_points=[schemas.MetricDataPointResponse(**p.to_dict()) for p in points],
        total=len(points),
    )


@app.post("/metrics/aggregate", response_model=schemas.MetricAggregateResponse)
async def aggregate_metrics(req: schemas.MetricAggregateRequest):
    """Aggregate metric data points."""
    result = repository.repo.aggregate(
        metric_name=req.metric_name,
        function=req.function,
        labels=req.labels,
        percentile=req.percentile,
    )
    return schemas.MetricAggregateResponse(
        result=result,
        function=req.function,
        metric_name=req.metric_name,
    )


@app.get("/metrics/recording-rules", response_model=schemas.RecordingRuleListResponse)
async def list_recording_rules():
    """List recording rules."""
    rules = repository.repo.list_recording_rules()
    return schemas.RecordingRuleListResponse(
        rules=[schemas.RecordingRuleResponse(**r.to_dict()) for r in rules],
        total=len(rules),
    )


@app.post("/metrics/recording-rules", response_model=schemas.RecordingRuleResponse, status_code=201)
async def create_recording_rule(req: schemas.RecordingRuleCreateRequest):
    """Create a new recording rule."""
    rr = repository.repo.create_recording_rule(req.model_dump())
    return schemas.RecordingRuleResponse(**rr.to_dict())


@app.get("/metrics/stats", response_model=schemas.MetricsStatsResponse)
async def metrics_stats():
    """Get metrics statistics."""
    stats = repository.repo.get_stats()
    return schemas.MetricsStatsResponse(**stats)
