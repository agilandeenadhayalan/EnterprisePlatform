"""
Log Aggregation Service — FastAPI application.

Log ingestion, querying, pattern detection, and retention for the
observability platform.

ROUTES:
  POST /logs/ingest              — Ingest a log entry
  POST /logs/query               — Query log entries
  GET  /logs/patterns            — List detected patterns
  GET  /logs/retention-policies  — List retention policies
  POST /logs/retention-policies  — Create retention policy
  GET  /logs/stats               — Log statistics
  GET  /health                   — Health check (provided by create_app)
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
    description="Log ingestion, querying, pattern detection, and retention for the observability platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/logs/ingest", response_model=schemas.LogEntryResponse, status_code=201)
async def ingest_log(req: schemas.LogIngestRequest):
    """Ingest a single log entry."""
    entry = repository.repo.ingest(req.model_dump())
    return schemas.LogEntryResponse(**entry.to_dict())


@app.post("/logs/query", response_model=schemas.LogEntryListResponse)
async def query_logs(req: schemas.LogQueryRequest):
    """Query log entries with filters."""
    entries = repository.repo.query(
        service_name=req.service_name,
        level=req.level,
        time_start=req.time_start,
        time_end=req.time_end,
        search=req.search,
        limit=req.limit,
    )
    return schemas.LogEntryListResponse(
        entries=[schemas.LogEntryResponse(**e.to_dict()) for e in entries],
        total=len(entries),
    )


@app.get("/logs/patterns", response_model=schemas.LogPatternListResponse)
async def list_patterns():
    """List detected log patterns."""
    patterns = repository.repo.list_patterns()
    return schemas.LogPatternListResponse(
        patterns=[schemas.LogPatternResponse(**p.to_dict()) for p in patterns],
        total=len(patterns),
    )


@app.get("/logs/retention-policies", response_model=schemas.RetentionPolicyListResponse)
async def list_retention_policies():
    """List log retention policies."""
    policies = repository.repo.list_retention_policies()
    return schemas.RetentionPolicyListResponse(
        policies=[schemas.RetentionPolicyResponse(**p.to_dict()) for p in policies],
        total=len(policies),
    )


@app.post("/logs/retention-policies", response_model=schemas.RetentionPolicyResponse, status_code=201)
async def create_retention_policy(req: schemas.RetentionPolicyCreateRequest):
    """Create a new retention policy."""
    policy = repository.repo.create_retention_policy(req.model_dump())
    return schemas.RetentionPolicyResponse(**policy.to_dict())


@app.get("/logs/stats", response_model=schemas.LogStatsResponse)
async def log_stats():
    """Get log statistics."""
    stats = repository.repo.get_stats()
    return schemas.LogStatsResponse(**stats)
