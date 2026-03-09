"""
Data Quality Service — FastAPI application.

Rule engine for data quality checks — validates data against defined rules
for completeness, freshness, accuracy, consistency, and uniqueness.

ROUTES:
  GET    /quality/rules                        — List all quality rules (supports ?dataset_id= filter)
  POST   /quality/rules                        — Create a quality rule
  GET    /quality/rules/{id}                   — Get rule details
  PATCH  /quality/rules/{id}                   — Update rule
  DELETE /quality/rules/{id}                   — Delete rule
  POST   /quality/run                          — Run quality checks for a dataset
  GET    /quality/results                      — Get quality check results (?rule_id=, ?status=)
  GET    /quality/results/{dataset_id}/summary — Summary of quality for a dataset
  GET    /health                               — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

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
    description="Data quality rule engine for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/quality/rules", response_model=list[schemas.QualityRuleResponse])
async def list_rules(
    dataset_id: str = Query(default=None, description="Filter rules by dataset"),
):
    """List all quality rules, optionally filtered by dataset."""
    rules = repository.repo.list_rules(dataset_id=dataset_id)
    return [schemas.QualityRuleResponse(**r.to_dict()) for r in rules]


@app.post("/quality/rules", response_model=schemas.QualityRuleResponse, status_code=201)
async def create_rule(body: schemas.QualityRuleCreate):
    """Create a new quality rule."""
    rule = repository.repo.create_rule(
        dataset_id=body.dataset_id,
        name=body.name,
        rule_type=body.rule_type,
        field=body.field,
        parameters=body.parameters,
        description=body.description,
        severity=body.severity,
    )
    return schemas.QualityRuleResponse(**rule.to_dict())


@app.get("/quality/rules/{rule_id}", response_model=schemas.QualityRuleResponse)
async def get_rule(rule_id: str):
    """Get a quality rule by ID."""
    rule = repository.repo.get_rule(rule_id)
    if not rule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return schemas.QualityRuleResponse(**rule.to_dict())


@app.patch("/quality/rules/{rule_id}", response_model=schemas.QualityRuleResponse)
async def update_rule(rule_id: str, body: schemas.QualityRuleUpdate):
    """Update a quality rule."""
    update_fields = body.model_dump(exclude_unset=True)
    rule = repository.repo.update_rule(rule_id, **update_fields)
    if not rule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return schemas.QualityRuleResponse(**rule.to_dict())


@app.delete("/quality/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str):
    """Delete a quality rule."""
    deleted = repository.repo.delete_rule(rule_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")


@app.post("/quality/run", response_model=schemas.QualityRunResponse)
async def run_quality_checks(body: schemas.QualityRunRequest):
    """Run all quality rules for a dataset against sample data."""
    results = repository.repo.run_checks(
        dataset_id=body.dataset_id,
        sample_data=body.sample_data,
    )

    result_responses = [schemas.QualityResultResponse(**r.to_dict()) for r in results]
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    errors = sum(1 for r in results if r.status == "error")

    return schemas.QualityRunResponse(
        dataset_id=body.dataset_id,
        results=result_responses,
        passed=passed,
        failed=failed,
        errors=errors,
    )


@app.get("/quality/results", response_model=schemas.QualityResultListResponse)
async def list_results(
    rule_id: str = Query(default=None, description="Filter by rule ID"),
    status: str = Query(default=None, description="Filter by status (passed, failed, error)"),
):
    """Get quality check results with optional filters."""
    results = repository.repo.list_results(rule_id=rule_id, status=status)
    return schemas.QualityResultListResponse(
        results=[schemas.QualityResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/quality/results/{dataset_id}/summary", response_model=schemas.QualitySummaryResponse)
async def quality_summary(dataset_id: str):
    """Get a quality summary for a dataset — scores, pass/fail counts."""
    summary = repository.repo.get_summary(dataset_id)
    return schemas.QualitySummaryResponse(**summary.to_dict())
