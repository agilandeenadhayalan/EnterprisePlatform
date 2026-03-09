"""
Data Governance Service — FastAPI application.

Manages data classification levels and access policies for datasets.
Classification levels: public, internal, confidential, restricted.

ROUTES:
  GET    /governance/policies                — List policies
  POST   /governance/policies                — Create policy
  GET    /governance/policies/{id}           — Get policy
  PATCH  /governance/policies/{id}           — Update policy
  DELETE /governance/policies/{id}           — Delete policy
  GET    /governance/classifications         — List classification levels
  POST   /governance/classify/{dataset_id}   — Classify a dataset
  GET    /health                             — Health check (provided by create_app)
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
    description="Data classification and governance policies",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/governance/policies", response_model=list[schemas.PolicyResponse])
async def list_policies():
    """List all governance policies."""
    policies = repository.repo.list_policies()
    return [schemas.PolicyResponse(**p.to_dict()) for p in policies]


@app.post("/governance/policies", response_model=schemas.PolicyResponse, status_code=201)
async def create_policy(body: schemas.PolicyCreate):
    """Create a new governance policy."""
    policy = repository.repo.create_policy(
        name=body.name,
        description=body.description,
        rules=body.rules,
        classification=body.classification,
        enforcement=body.enforcement,
        owner=body.owner,
    )
    return schemas.PolicyResponse(**policy.to_dict())


@app.get("/governance/policies/{policy_id}", response_model=schemas.PolicyResponse)
async def get_policy(policy_id: str):
    """Get a governance policy by ID."""
    policy = repository.repo.get_policy(policy_id)
    if not policy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return schemas.PolicyResponse(**policy.to_dict())


@app.patch("/governance/policies/{policy_id}", response_model=schemas.PolicyResponse)
async def update_policy(policy_id: str, body: schemas.PolicyUpdate):
    """Update a governance policy."""
    update_fields = body.model_dump(exclude_unset=True)
    policy = repository.repo.update_policy(policy_id, **update_fields)
    if not policy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return schemas.PolicyResponse(**policy.to_dict())


@app.delete("/governance/policies/{policy_id}", status_code=204)
async def delete_policy(policy_id: str):
    """Delete a governance policy."""
    deleted = repository.repo.delete_policy(policy_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")


@app.get("/governance/classifications", response_model=list[schemas.ClassificationLevelResponse])
async def list_classifications():
    """List all available classification levels with descriptions."""
    levels = repository.repo.get_classification_levels()
    return [schemas.ClassificationLevelResponse(**lvl) for lvl in levels]


@app.post("/governance/classify/{dataset_id}", response_model=schemas.ClassificationResponse)
async def classify_dataset(dataset_id: str, body: schemas.ClassifyRequest):
    """Classify a dataset with a specific level."""
    valid_levels = ["public", "internal", "confidential", "restricted"]
    if body.level not in valid_levels:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid classification level '{body.level}'. Must be one of: {', '.join(valid_levels)}",
        )

    classification = repository.repo.classify_dataset(
        dataset_id=dataset_id,
        level=body.level,
        reason=body.reason,
        classified_by=body.classified_by,
        pii_fields=body.pii_fields,
        retention_days=body.retention_days,
    )
    return schemas.ClassificationResponse(**classification.to_dict())
