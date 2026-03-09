"""
Data Retention Service — FastAPI application.

Enforces TTL policies on ClickHouse tables and MinIO buckets.
Tracks retention enforcement runs and space reclaimed.

ROUTES:
  GET    /retention/policies      — List retention policies
  POST   /retention/policies      — Create retention policy
  GET    /retention/policies/{id} — Get policy details
  PATCH  /retention/policies/{id} — Update policy
  DELETE /retention/policies/{id} — Delete policy
  POST   /retention/enforce       — Run retention enforcement
  GET    /retention/stats         — Retention stats (data deleted, space reclaimed)
  GET    /health                  — Health check (provided by create_app)
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
    description="Data retention policy enforcement for ClickHouse and MinIO",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/retention/policies", response_model=list[schemas.RetentionPolicyResponse])
async def list_policies():
    """List all retention policies."""
    policies = repository.repo.list_policies()
    return [schemas.RetentionPolicyResponse(**p.to_dict()) for p in policies]


@app.post("/retention/policies", response_model=schemas.RetentionPolicyResponse, status_code=201)
async def create_policy(body: schemas.RetentionPolicyCreate):
    """Create a new retention policy."""
    policy = repository.repo.create_policy(
        name=body.name,
        target=body.target,
        target_type=body.target_type,
        retention_days=body.retention_days,
        description=body.description,
        enabled=body.enabled,
    )
    return schemas.RetentionPolicyResponse(**policy.to_dict())


@app.get("/retention/policies/{policy_id}", response_model=schemas.RetentionPolicyResponse)
async def get_policy(policy_id: str):
    """Get a retention policy by ID."""
    policy = repository.repo.get_policy(policy_id)
    if not policy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return schemas.RetentionPolicyResponse(**policy.to_dict())


@app.patch("/retention/policies/{policy_id}", response_model=schemas.RetentionPolicyResponse)
async def update_policy(policy_id: str, body: schemas.RetentionPolicyUpdate):
    """Update a retention policy."""
    update_fields = body.model_dump(exclude_unset=True)
    policy = repository.repo.update_policy(policy_id, **update_fields)
    if not policy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return schemas.RetentionPolicyResponse(**policy.to_dict())


@app.delete("/retention/policies/{policy_id}", status_code=204)
async def delete_policy(policy_id: str):
    """Delete a retention policy."""
    deleted = repository.repo.delete_policy(policy_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")


@app.post("/retention/enforce", response_model=schemas.RetentionEnforceResponse)
async def enforce_retention():
    """Run retention enforcement — check all enabled policies, delete expired data."""
    runs = repository.repo.enforce_policies()
    return schemas.RetentionEnforceResponse(
        runs=[schemas.RetentionRunResponse(**r.to_dict()) for r in runs],
        total_policies_checked=len(runs),
        total_records_deleted=sum(r.records_deleted for r in runs),
        total_bytes_reclaimed=sum(r.bytes_reclaimed for r in runs),
    )


@app.get("/retention/stats", response_model=schemas.RetentionStatsResponse)
async def retention_stats():
    """Get retention statistics — total data deleted, space reclaimed."""
    stats = repository.repo.get_stats()
    return schemas.RetentionStatsResponse(**stats)
