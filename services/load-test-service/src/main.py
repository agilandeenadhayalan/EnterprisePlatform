"""
Load Test Service — FastAPI application.

Load test scenario management and results analysis.

ROUTES:
  GET    /load-tests/scenarios           — List test scenarios
  POST   /load-tests/scenarios           — Create scenario
  GET    /load-tests/runs                — List test runs
  POST   /load-tests/runs                — Start a load test run
  GET    /load-tests/runs/{id}           — Get run details
  PATCH  /load-tests/runs/{id}           — Update run status/results
  POST   /load-tests/runs/{id}/results   — Record results for a run
  GET    /load-tests/runs/{id}/analysis  — Get latency analysis
  GET    /health                         — Health check (provided by create_app)
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
    description="Load test scenario management and results analysis",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/load-tests/scenarios", response_model=list[schemas.ScenarioResponse])
async def list_scenarios():
    """List all test scenarios."""
    scenarios = repository.repo.list_scenarios()
    return [schemas.ScenarioResponse(**s.to_dict()) for s in scenarios]


@app.post("/load-tests/scenarios", response_model=schemas.ScenarioResponse, status_code=201)
async def create_scenario(body: schemas.ScenarioCreate):
    """Create a test scenario."""
    scenario = repository.repo.create_scenario(
        name=body.name,
        pattern=body.pattern,
        target_rps=body.target_rps,
        duration_seconds=body.duration_seconds,
        config=body.config,
    )
    return schemas.ScenarioResponse(**scenario.to_dict())


@app.get("/load-tests/runs", response_model=list[schemas.RunResponse])
async def list_runs():
    """List all test runs."""
    runs = repository.repo.list_runs()
    return [schemas.RunResponse(**r.to_dict()) for r in runs]


@app.post("/load-tests/runs", response_model=schemas.RunResponse, status_code=201)
async def create_run(body: schemas.RunCreate):
    """Start a load test run."""
    scenario = repository.repo.get_scenario(body.scenario_id)
    if not scenario:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Scenario '{body.scenario_id}' not found")
    run = repository.repo.create_run(scenario_id=body.scenario_id)
    return schemas.RunResponse(**run.to_dict())


@app.get("/load-tests/runs/{run_id}", response_model=schemas.RunResponse)
async def get_run(run_id: str):
    """Get run details."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.RunResponse(**run.to_dict())


@app.patch("/load-tests/runs/{run_id}", response_model=schemas.RunResponse)
async def update_run(run_id: str, body: schemas.RunUpdate):
    """Update run status/results."""
    update_fields = body.model_dump(exclude_unset=True)
    run = repository.repo.update_run(run_id, **update_fields)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.RunResponse(**run.to_dict())


@app.post("/load-tests/runs/{run_id}/results", response_model=schemas.ResultResponse, status_code=201)
async def record_result(run_id: str, body: schemas.ResultCreate):
    """Record results for a run."""
    result = repository.repo.record_result(
        run_id=run_id,
        p50_ms=body.p50_ms,
        p95_ms=body.p95_ms,
        p99_ms=body.p99_ms,
        error_rate=body.error_rate,
        total_requests=body.total_requests,
        throughput_rps=body.throughput_rps,
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return schemas.ResultResponse(**result.to_dict())


@app.get("/load-tests/runs/{run_id}/analysis", response_model=schemas.AnalysisResponse)
async def get_analysis(run_id: str):
    """Get latency analysis for a run (p50/p95/p99)."""
    run = repository.repo.get_run(run_id)
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    analysis = repository.repo.get_analysis(run_id)
    return schemas.AnalysisResponse(**analysis)
