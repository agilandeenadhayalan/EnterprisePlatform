"""
Bucketing Service — FastAPI application.

Deterministic user bucketing and traffic allocation for experiments.

ROUTES:
  POST /bucketing/assign                        — Assign user to bucket
  GET  /bucketing/assignment/{exp_id}/{user_id}  — Get assignment
  GET  /bucketing/assignments                    — List assignments
  GET  /bucketing/allocation/{exp_id}            — Get traffic allocation
  POST /bucketing/allocation                     — Set allocation
  POST /bucketing/bulk-assign                    — Bulk assign users
  GET  /bucketing/stats                          — Stats
  GET  /health                                   — Health check
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
    description="Deterministic user bucketing and traffic allocation for experiments",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/bucketing/assign", response_model=schemas.BucketAssignmentResponse, status_code=201)
async def assign_user(req: schemas.AssignRequest):
    """Assign a user to a bucket for an experiment."""
    assignment = repository.repo.assign_user(req.experiment_id, req.user_id, req.variant_weights)
    return schemas.BucketAssignmentResponse(**assignment.to_dict())


@app.get("/bucketing/assignment/{experiment_id}/{user_id}", response_model=schemas.BucketAssignmentResponse)
async def get_assignment(experiment_id: str, user_id: str):
    """Get a user's bucket assignment."""
    assignment = repository.repo.get_assignment(experiment_id, user_id)
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment not found for experiment '{experiment_id}' and user '{user_id}'")
    return schemas.BucketAssignmentResponse(**assignment.to_dict())


@app.get("/bucketing/assignments", response_model=schemas.BucketAssignmentListResponse)
async def list_assignments(
    experiment_id: Optional[str] = Query(default=None, description="Filter by experiment ID"),
):
    """List all bucket assignments."""
    assignments = repository.repo.list_assignments(experiment_id)
    return schemas.BucketAssignmentListResponse(
        assignments=[schemas.BucketAssignmentResponse(**a.to_dict()) for a in assignments],
        total=len(assignments),
    )


@app.get("/bucketing/allocation/{experiment_id}", response_model=schemas.TrafficAllocationResponse)
async def get_allocation(experiment_id: str):
    """Get traffic allocation for an experiment."""
    alloc = repository.repo.get_allocation(experiment_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Allocation not found for experiment '{experiment_id}'")
    return schemas.TrafficAllocationResponse(**alloc.to_dict())


@app.post("/bucketing/allocation", response_model=schemas.TrafficAllocationResponse, status_code=201)
async def set_allocation(req: schemas.SetAllocationRequest):
    """Set traffic allocation for an experiment."""
    alloc = repository.repo.set_allocation(req.experiment_id, req.variant_weights)
    return schemas.TrafficAllocationResponse(**alloc.to_dict())


@app.post("/bucketing/bulk-assign", response_model=schemas.BulkAssignResponse, status_code=201)
async def bulk_assign(req: schemas.BulkAssignRequest):
    """Bulk assign users to buckets."""
    assignments = repository.repo.bulk_assign(req.experiment_id, req.user_ids, req.variant_weights)
    return schemas.BulkAssignResponse(
        assignments=[schemas.BucketAssignmentResponse(**a.to_dict()) for a in assignments],
        total=len(assignments),
    )


@app.get("/bucketing/stats", response_model=schemas.BucketStatsResponse)
async def bucket_stats():
    """Get bucketing statistics."""
    stats = repository.repo.get_stats()
    return schemas.BucketStatsResponse(
        total_assignments=stats["total_assignments"],
        by_experiment=stats["by_experiment"],
        config=schemas.BucketConfigResponse(**stats["config"]),
    )
