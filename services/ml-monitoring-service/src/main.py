"""
ML Monitoring Service — FastAPI application.

Drift detection (PSI, KS, JSD), concept drift analysis,
reference distribution management, and alerting.

ROUTES:
  POST /monitoring/drift/detect     — Run drift detection
  GET  /monitoring/drift/results    — List drift detection results
  POST /monitoring/drift/reference  — Set reference distribution
  GET  /monitoring/drift/dashboard  — Drift dashboard (all features)
  POST /monitoring/concept-drift    — Detect concept drift
  GET  /monitoring/alerts           — List drift alerts
  GET  /health                      — Health check (provided by create_app)
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
    description="Drift detection (PSI, KS, JSD), concept drift analysis, and alerting",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/monitoring/drift/detect", response_model=schemas.DriftResultResponse)
async def detect_drift(req: schemas.DriftDetectRequest):
    """Run drift detection on a feature."""
    result = repository.repo.detect_drift(
        feature_name=req.feature_name,
        reference_data=req.reference_data,
        current_data=req.current_data,
        method=req.method,
    )
    return schemas.DriftResultResponse(**result.to_dict())


@app.get("/monitoring/drift/results", response_model=schemas.DriftResultListResponse)
async def list_drift_results():
    """List all drift detection results."""
    results = repository.repo.list_drift_results()
    return schemas.DriftResultListResponse(
        results=[schemas.DriftResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.post("/monitoring/drift/reference", response_model=schemas.ReferenceDistributionResponse, status_code=201)
async def set_reference(req: schemas.ReferenceSetRequest):
    """Set reference distribution for a feature."""
    ref = repository.repo.set_reference(req.feature_name, req.values)
    return schemas.ReferenceDistributionResponse(**ref.to_dict())


@app.get("/monitoring/drift/dashboard", response_model=schemas.DriftDashboardResponse)
async def drift_dashboard():
    """Get drift dashboard for all monitored features."""
    dash = repository.repo.get_dashboard()
    features = []
    for f in dash["features"]:
        latest = None
        if f["latest_result"]:
            latest = schemas.DriftResultResponse(**f["latest_result"].to_dict())
        features.append(schemas.DashboardFeature(
            feature_name=f["feature_name"],
            latest_result=latest,
            has_reference=f["has_reference"],
            alert_count=f["alert_count"],
        ))
    return schemas.DriftDashboardResponse(
        features=features,
        total_features=dash["total_features"],
        drifted_count=dash["drifted_count"],
    )


@app.post("/monitoring/concept-drift", response_model=schemas.ConceptDriftResultResponse)
async def detect_concept_drift(req: schemas.ConceptDriftRequest):
    """Detect concept drift from predictions and actuals."""
    result = repository.repo.detect_concept_drift(
        model_name=req.model_name,
        predictions=req.predictions,
        actuals=req.actuals,
    )
    return schemas.ConceptDriftResultResponse(**result.to_dict())


@app.get("/monitoring/alerts", response_model=schemas.DriftAlertListResponse)
async def list_alerts():
    """List all drift alerts."""
    alerts = repository.repo.list_alerts()
    return schemas.DriftAlertListResponse(
        alerts=[schemas.DriftAlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
    )
