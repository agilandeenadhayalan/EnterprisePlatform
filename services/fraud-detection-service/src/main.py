"""
Fraud Detection Service — FastAPI application.

Fraud detection with ensemble scoring, rule management, and graph analysis.

ROUTES:
  GET  /fraud/alerts                — List fraud alerts
  GET  /fraud/alerts/{id}           — Get fraud alert
  POST /fraud/alerts/{id}/resolve   — Resolve fraud alert
  POST /fraud/score                 — Score transaction
  GET  /fraud/rules                 — List fraud rules
  POST /fraud/rules                 — Create fraud rule
  POST /fraud/rules/{id}/toggle     — Toggle rule active status
  POST /fraud/analyze-graph         — Graph analysis
  GET  /fraud/stats                 — Fraud statistics
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


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Fraud detection with ensemble scoring, rule management, and graph analysis",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/fraud/alerts", response_model=schemas.FraudAlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    alert_type: Optional[str] = Query(default=None, description="Filter by alert_type"),
):
    """List all fraud alerts."""
    alerts = repository.repo.list_alerts(status=status, alert_type=alert_type)
    return schemas.FraudAlertListResponse(
        alerts=[schemas.FraudAlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
    )


@app.get("/fraud/alerts/{alert_id}", response_model=schemas.FraudAlertResponse)
async def get_alert(alert_id: str):
    """Get a single fraud alert by ID."""
    alert = repository.repo.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.FraudAlertResponse(**alert.to_dict())


@app.post("/fraud/alerts/{alert_id}/resolve", response_model=schemas.FraudAlertResponse)
async def resolve_alert(alert_id: str):
    """Resolve a fraud alert."""
    alert = repository.repo.resolve_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.FraudAlertResponse(**alert.to_dict())


@app.post("/fraud/score", response_model=schemas.TransactionScoreResponse, status_code=201)
async def score_transaction(req: schemas.ScoreTransactionRequest):
    """Score a transaction for fraud."""
    score = repository.repo.score_transaction(req.model_dump())
    return schemas.TransactionScoreResponse(**score.to_dict())


@app.get("/fraud/rules", response_model=schemas.FraudRuleListResponse)
async def list_rules():
    """List all fraud rules."""
    rules = repository.repo.list_rules()
    return schemas.FraudRuleListResponse(
        rules=[schemas.FraudRuleResponse(**r.to_dict()) for r in rules],
        total=len(rules),
    )


@app.post("/fraud/rules", response_model=schemas.FraudRuleResponse, status_code=201)
async def create_rule(req: schemas.FraudRuleCreateRequest):
    """Create a new fraud rule."""
    rule = repository.repo.create_rule(req.model_dump())
    return schemas.FraudRuleResponse(**rule.to_dict())


@app.post("/fraud/rules/{rule_id}/toggle", response_model=schemas.FraudRuleResponse)
async def toggle_rule(rule_id: str):
    """Toggle a fraud rule's active status."""
    rule = repository.repo.toggle_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return schemas.FraudRuleResponse(**rule.to_dict())


@app.post("/fraud/analyze-graph", response_model=schemas.GraphAnalysisResponse)
async def analyze_graph(req: schemas.GraphAnalysisRequest):
    """Run graph analysis on user connections."""
    result = repository.repo.analyze_graph(req.user_ids)
    return schemas.GraphAnalysisResponse(**result)


@app.get("/fraud/stats", response_model=schemas.FraudStatsResponse)
async def fraud_stats():
    """Get fraud statistics."""
    stats = repository.repo.get_stats()
    return schemas.FraudStatsResponse(**stats)
