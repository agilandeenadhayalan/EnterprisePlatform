"""
Pydantic request/response schemas for the Training Data Service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class DatasetCreateRequest(BaseModel):
    """Request to create a new dataset specification."""
    name: str = Field(..., description="Dataset name")
    feature_names: list[str] = Field(..., description="List of feature column names")
    label_column: str = Field(..., description="Target label column name")
    date_range: dict = Field(default_factory=dict, description="Date range filter (start, end)")
    split_ratio: dict = Field(default_factory=lambda: {"train": 0.7, "val": 0.15, "test": 0.15}, description="Train/val/test split ratios")
    sampling_strategy: str = Field(default="random", description="Sampling strategy: random, stratified, time_based")


# ── Response schemas ──


class DatasetSpecResponse(BaseModel):
    """A dataset specification."""
    id: str
    name: str
    feature_names: list[str]
    label_column: str
    date_range: dict
    split_ratio: dict
    sampling_strategy: str
    status: str
    created_at: str


class DatasetSpecListResponse(BaseModel):
    """List of dataset specifications."""
    datasets: list[DatasetSpecResponse]
    total: int


class DatasetStatsResponse(BaseModel):
    """Dataset statistical summary."""
    row_count: int
    feature_count: int
    label_distribution: dict
    missing_values_pct: float


class DataSplitResponse(BaseModel):
    """Dataset split sizes."""
    train_size: int
    val_size: int
    test_size: int


class DatasetSampleResponse(BaseModel):
    """A sample of rows from the dataset."""
    dataset_id: str
    columns: list[str]
    rows: list[dict]
    total_sampled: int
