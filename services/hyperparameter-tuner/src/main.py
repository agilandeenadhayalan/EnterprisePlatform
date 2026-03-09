"""
Hyperparameter Tuner — FastAPI application.

Grid/random/Bayesian hyperparameter search orchestrator. Creates search
sessions, manages trials, and identifies best parameter configurations.

ROUTES:
  POST /tuning/searches             — Create a hyperparameter search
  GET  /tuning/searches             — List searches
  GET  /tuning/searches/{id}        — Search details + best params
  GET  /tuning/searches/{id}/trials — List all trials with metrics
  GET  /tuning/searches/{id}/best   — Get best trial
  GET  /health                      — Health check (provided by create_app)
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
from models import ParamSpace


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Grid/random/Bayesian hyperparameter search orchestrator",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/tuning/searches", response_model=schemas.HyperparameterSearchResponse, status_code=201)
async def create_search(body: schemas.SearchCreateRequest):
    """Create a new hyperparameter search."""
    param_space = [
        ParamSpace(
            param_name=p.param_name,
            type=p.type,
            min=p.min,
            max=p.max,
            choices=p.choices,
        )
        for p in body.param_space
    ]
    search = repository.repo.create_search(
        model_type=body.model_type,
        search_strategy=body.search_strategy,
        param_space=param_space,
        objective_metric=body.objective_metric,
    )
    return schemas.HyperparameterSearchResponse(**search.to_dict())


@app.get("/tuning/searches", response_model=schemas.SearchListResponse)
async def list_searches(
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all hyperparameter searches."""
    searches = repository.repo.list_searches(status=status)
    return schemas.SearchListResponse(
        searches=[schemas.HyperparameterSearchResponse(**s.to_dict()) for s in searches],
        total=len(searches),
    )


@app.get("/tuning/searches/{search_id}", response_model=schemas.HyperparameterSearchResponse)
async def get_search(search_id: str):
    """Get details for a specific hyperparameter search."""
    search = repository.repo.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail=f"Search {search_id} not found")
    return schemas.HyperparameterSearchResponse(**search.to_dict())


@app.get("/tuning/searches/{search_id}/trials", response_model=schemas.TrialListResponse)
async def list_trials(search_id: str):
    """List all trials for a hyperparameter search."""
    search = repository.repo.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail=f"Search {search_id} not found")
    trials = repository.repo.get_trials(search_id)
    return schemas.TrialListResponse(
        trials=[schemas.SearchTrialResponse(**t.to_dict()) for t in trials],
        total=len(trials),
    )


@app.get("/tuning/searches/{search_id}/best", response_model=schemas.SearchTrialResponse)
async def get_best_trial(search_id: str):
    """Get the best trial from a hyperparameter search."""
    search = repository.repo.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail=f"Search {search_id} not found")
    trial = repository.repo.get_best_trial(search_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"No best trial found for search {search_id}")
    return schemas.SearchTrialResponse(**trial.to_dict())
