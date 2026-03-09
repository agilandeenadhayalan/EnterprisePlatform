"""
Pydantic request/response schemas for the batch prediction API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class BatchJobCreateRequest(BaseModel):
    """Request to submit a new batch prediction job."""
    model_name: str = Field(..., description="Name of the model to use")
    dataset_id: str = Field(..., description="ID of the dataset to score")
    output_format: str = Field(default="json", description="Output format: json or parquet")


# ── Response schemas ──


class BatchJobResponse(BaseModel):
    """Batch job details."""
    id: str
    model_name: str
    dataset_id: str
    status: str
    output_format: str
    total_records: int
    processed_records: int
    created_at: str
    completed_at: Optional[str] = None


class BatchJobListResponse(BaseModel):
    """List of batch jobs."""
    jobs: list[BatchJobResponse]
    total: int


class BatchResultResponse(BaseModel):
    """A single batch result."""
    job_id: str
    entity_id: str
    prediction: float
    confidence: float


class BatchResultListResponse(BaseModel):
    """Paginated list of batch results."""
    results: list[BatchResultResponse]
    total: int
    page: int
    page_size: int
