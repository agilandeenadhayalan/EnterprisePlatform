"""
Trace Collector Service — FastAPI application.

Distributed trace collection, assembly, dependency mapping, and analysis
for the observability platform.

ROUTES:
  POST /traces/spans               — Submit a span
  GET  /traces/{trace_id}          — Get assembled trace
  GET  /traces                     — List recent traces
  GET  /traces/{trace_id}/spans    — Get spans for a trace
  GET  /traces/dependencies        — Service dependency graph
  POST /traces/analyze             — Analyze service performance
  GET  /traces/stats               — Trace statistics
  GET  /health                     — Health check (provided by create_app)
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
    description="Distributed trace collection, assembly, dependency mapping, and analysis for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──
# NOTE: Static paths like /traces/dependencies and /traces/stats must be
# registered BEFORE the parameterised /traces/{trace_id} route so FastAPI
# matches them first.


@app.post("/traces/spans", response_model=schemas.SpanResponse, status_code=201)
async def submit_span(req: schemas.SpanSubmitRequest):
    """Submit a span to the trace collector."""
    span = repository.repo.submit_span(req.model_dump())
    return schemas.SpanResponse(**span.to_dict())


@app.get("/traces/dependencies", response_model=schemas.DependencyListResponse)
async def get_dependencies():
    """Service dependency graph derived from traces."""
    deps = repository.repo.get_dependencies()
    return schemas.DependencyListResponse(
        dependencies=[schemas.ServiceDependencyResponse(**d.to_dict()) for d in deps],
        total=len(deps),
    )


@app.post("/traces/analyze", response_model=schemas.AnalyzeResponse)
async def analyze_service(req: schemas.AnalyzeRequest):
    """Analyze service performance based on spans."""
    result = repository.repo.analyze_service(req.service_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"No spans found for service '{req.service_name}'")
    return schemas.AnalyzeResponse(**result)


@app.get("/traces/stats", response_model=schemas.TraceStatsResponse)
async def trace_stats():
    """Get trace statistics."""
    stats = repository.repo.get_stats()
    return schemas.TraceStatsResponse(**stats)


@app.get("/traces", response_model=schemas.TraceListResponse)
async def list_traces():
    """List recent trace summaries."""
    summaries = repository.repo.list_traces()
    return schemas.TraceListResponse(
        traces=[schemas.TraceSummary(**s) for s in summaries],
        total=len(summaries),
    )


@app.get("/traces/{trace_id}", response_model=schemas.TraceResponse)
async def get_trace(trace_id: str):
    """Get an assembled trace by ID."""
    trace = repository.repo.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return schemas.TraceResponse(
        trace_id=trace.trace_id,
        spans=[schemas.SpanResponse(**s.to_dict()) for s in trace.spans],
        service_count=trace.service_count,
        total_duration_ms=trace.total_duration_ms,
        root_span=trace.root_span,
    )


@app.get("/traces/{trace_id}/spans", response_model=schemas.SpanListResponse)
async def get_trace_spans(trace_id: str):
    """Get all spans for a trace, ordered by start_time."""
    spans = repository.repo.get_spans(trace_id)
    if not spans:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return schemas.SpanListResponse(
        spans=[schemas.SpanResponse(**s.to_dict()) for s in spans],
        total=len(spans),
    )
