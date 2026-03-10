"""
AB Test Analytics Service — FastAPI application.

Statistical analysis for A/B tests including z-tests, power calculations,
and sequential testing.

ROUTES:
  POST /ab-analytics/test           — Run statistical test
  GET  /ab-analytics/results        — List results
  GET  /ab-analytics/results/{id}   — Get result
  POST /ab-analytics/power          — Power/sample size calculation
  POST /ab-analytics/sequential     — Sequential test
  GET  /ab-analytics/sequential     — List sequential results
  GET  /ab-analytics/stats          — Stats
  GET  /health                      — Health check
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
    description="Statistical analysis for A/B tests including z-tests, power calculations, and sequential testing",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/ab-analytics/test", response_model=schemas.ABTestResultResponse, status_code=201)
async def run_test(req: schemas.RunTestRequest):
    """Run a statistical test on A/B test data."""
    result = repository.repo.run_test(req.model_dump())
    return schemas.ABTestResultResponse(**result.to_dict())


@app.get("/ab-analytics/results", response_model=schemas.ABTestResultListResponse)
async def list_results(
    experiment_id: Optional[str] = Query(default=None, description="Filter by experiment ID"),
):
    """List all A/B test results."""
    results = repository.repo.list_results(experiment_id)
    return schemas.ABTestResultListResponse(
        results=[schemas.ABTestResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/ab-analytics/results/{result_id}", response_model=schemas.ABTestResultResponse)
async def get_result(result_id: str):
    """Get a specific A/B test result."""
    result = repository.repo.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")
    return schemas.ABTestResultResponse(**result.to_dict())


@app.post("/ab-analytics/power", response_model=schemas.PowerCalcResponse)
async def power_calculation(req: schemas.PowerCalcRequest):
    """Calculate required sample size for given power and MDE."""
    result = repository.repo.calc_power(req.alpha, req.power, req.mde)
    return schemas.PowerCalcResponse(**result)


@app.post("/ab-analytics/sequential", response_model=schemas.SequentialTestResultResponse, status_code=201)
async def sequential_test(req: schemas.SequentialTestRequest):
    """Run a sequential test analysis."""
    result = repository.repo.run_sequential_test(req.model_dump())
    return schemas.SequentialTestResultResponse(**result.to_dict())


@app.get("/ab-analytics/sequential", response_model=schemas.SequentialTestListResponse)
async def list_sequential():
    """List all sequential test results."""
    results = repository.repo.list_sequential_results()
    return schemas.SequentialTestListResponse(
        results=[schemas.SequentialTestResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/ab-analytics/stats", response_model=schemas.ABTestStatsResponse)
async def test_stats():
    """Get A/B test statistics."""
    stats = repository.repo.get_stats()
    return schemas.ABTestStatsResponse(**stats)
