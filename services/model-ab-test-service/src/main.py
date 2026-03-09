"""
Model A/B Test Service — FastAPI application.

A/B test and shadow deployment routing for ML models. Manages test creation,
traffic routing, outcome recording, and statistical significance testing.

ROUTES:
  POST /ab-tests                    — Create an A/B test
  GET  /ab-tests                    — List active tests
  GET  /ab-tests/{id}               — Test details + variant metrics
  POST /ab-tests/{id}/route         — Route a request
  POST /ab-tests/{id}/record        — Record outcome for a variant
  POST /ab-tests/{id}/conclude      — End test, declare winner
  GET  /ab-tests/{id}/significance  — Statistical significance check
  GET  /health                      — Health check (provided by create_app)
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
    description="A/B test and shadow deployment routing for ML models",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/ab-tests", response_model=schemas.ABTestResponse, status_code=201)
async def create_ab_test(request: schemas.ABTestCreateRequest):
    """Create a new A/B test."""
    test = repository.repo.create_test(
        name=request.name,
        champion_model=request.champion_model,
        challenger_model=request.challenger_model,
        traffic_split=request.traffic_split,
    )
    return schemas.ABTestResponse(**test.to_dict())


@app.get("/ab-tests", response_model=schemas.ABTestListResponse)
async def list_ab_tests(
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List A/B tests, optionally filtered by status."""
    tests = repository.repo.list_tests(status=status)
    return schemas.ABTestListResponse(
        tests=[schemas.ABTestResponse(**t.to_dict()) for t in tests],
        total=len(tests),
    )


@app.get("/ab-tests/{test_id}", response_model=schemas.ABTestResponse)
async def get_ab_test(test_id: str):
    """Get A/B test details and variant metrics."""
    test = repository.repo.get_test(test_id)
    if test is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"A/B test '{test_id}' not found")
    return schemas.ABTestResponse(**test.to_dict())


@app.post("/ab-tests/{test_id}/route", response_model=schemas.RouteResponse)
async def route_request(test_id: str, request: schemas.RouteRequest):
    """Route a request to champion or challenger variant."""
    result = repository.repo.route_request(test_id, request.request_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"A/B test '{test_id}' not found or not active",
        )
    return schemas.RouteResponse(**result)


@app.post("/ab-tests/{test_id}/record", response_model=schemas.ABTestResponse)
async def record_outcome(test_id: str, request: schemas.RecordOutcomeRequest):
    """Record an outcome for a variant."""
    test = repository.repo.record_outcome(test_id, request.variant, request.value)
    if test is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"A/B test '{test_id}' not found")
    return schemas.ABTestResponse(**test.to_dict())


@app.post("/ab-tests/{test_id}/conclude", response_model=schemas.ABTestResponse)
async def conclude_test(test_id: str):
    """Conclude an A/B test and declare a winner."""
    test = repository.repo.conclude_test(test_id)
    if test is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"A/B test '{test_id}' not found or already concluded",
        )
    return schemas.ABTestResponse(**test.to_dict())


@app.get("/ab-tests/{test_id}/significance", response_model=schemas.SignificanceResponse)
async def check_significance(test_id: str):
    """Check statistical significance of A/B test results."""
    result = repository.repo.check_significance(test_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"A/B test '{test_id}' not found")
    return schemas.SignificanceResponse(**result.to_dict())
