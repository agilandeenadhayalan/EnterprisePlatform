"""
Pydantic response schemas for the Bucketing service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class BucketAssignmentResponse(BaseModel):
    id: str
    experiment_id: str
    user_id: str
    variant: str
    bucket_hash: str
    assigned_at: str


class BucketAssignmentListResponse(BaseModel):
    assignments: List[BucketAssignmentResponse]
    total: int


class AssignRequest(BaseModel):
    experiment_id: str
    user_id: str
    variant_weights: Dict[str, float]


class BulkAssignRequest(BaseModel):
    experiment_id: str
    user_ids: List[str]
    variant_weights: Dict[str, float]


class BulkAssignResponse(BaseModel):
    assignments: List[BucketAssignmentResponse]
    total: int


class TrafficAllocationResponse(BaseModel):
    experiment_id: str
    variant_weights: Dict[str, float]
    total_allocated: int


class SetAllocationRequest(BaseModel):
    experiment_id: str
    variant_weights: Dict[str, float]


class BucketConfigResponse(BaseModel):
    hash_seed: str
    hash_algorithm: str


class BucketStatsResponse(BaseModel):
    total_assignments: int
    by_experiment: Dict[str, int]
    config: BucketConfigResponse
