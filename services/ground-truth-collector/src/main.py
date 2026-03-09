"""
Ground Truth Collector — FastAPI application.

Delayed label collection and joining for ML model evaluation.
Collects ground truth labels, joins with predictions, and computes
coverage and performance metrics over time.

ROUTES:
  POST /ground-truth/labels       — Submit ground truth labels
  GET  /ground-truth/labels       — List labels
  POST /ground-truth/join         — Join predictions with ground truth
  GET  /ground-truth/coverage     — Label coverage statistics
  GET  /ground-truth/performance  — Model performance over time
  GET  /health                    — Health check (provided by create_app)
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
    description="Delayed label collection and joining for ML model evaluation",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/ground-truth/labels", response_model=schemas.LabelsSubmitResponse, status_code=201)
async def submit_labels(req: schemas.LabelsSubmitRequest):
    """Submit ground truth labels."""
    items = [item.model_dump() for item in req.labels]
    count = repository.repo.submit_labels(items)
    return schemas.LabelsSubmitResponse(ingested=count, message=f"Ingested {count} labels")


@app.get("/ground-truth/labels", response_model=schemas.LabelListResponse)
async def list_labels(
    model_name: Optional[str] = Query(default=None, description="Filter by model"),
    limit: int = Query(default=50, description="Max results"),
):
    """List ground truth labels."""
    labels = repository.repo.list_labels(model_name=model_name, limit=limit)
    return schemas.LabelListResponse(
        labels=[schemas.GroundTruthLabelResponse(**l.to_dict()) for l in labels],
        total=len(labels),
    )


@app.post("/ground-truth/join", response_model=schemas.JoinResponse)
async def join_predictions(req: schemas.JoinRequest):
    """Join predictions with ground truth for a model."""
    pairs = repository.repo.join_predictions(req.model_name)
    return schemas.JoinResponse(
        model_name=req.model_name,
        pairs=[schemas.PredictionGroundTruthPairResponse(**p.to_dict()) for p in pairs],
        total=len(pairs),
    )


@app.get("/ground-truth/coverage", response_model=schemas.CoverageListResponse)
async def label_coverage():
    """Get label coverage statistics."""
    coverage = repository.repo.get_coverage()
    return schemas.CoverageListResponse(
        coverage=[schemas.LabelCoverageResponse(**c.to_dict()) for c in coverage],
        total_models=len(coverage),
    )


@app.get("/ground-truth/performance", response_model=schemas.PerformanceResponse)
async def model_performance():
    """Get model performance over time."""
    perf = repository.repo.get_performance()
    models = []
    for p in perf:
        buckets = [schemas.PerformanceBucket(**b) for b in p["buckets"]]
        models.append(schemas.ModelPerformance(
            model_name=p["model_name"],
            overall_mae=p["overall_mae"],
            buckets=buckets,
        ))
    return schemas.PerformanceResponse(models=models, total_models=len(models))
