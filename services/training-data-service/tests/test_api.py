"""
Tests for the Training Data Service API.

Covers: dataset creation, listing, preparation, stats, sampling, splits, edge cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_datasets(client: AsyncClient):
    """List all datasets returns seeded data."""
    resp = await client.get("/training-data/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["datasets"]) == 3


@pytest.mark.anyio
async def test_list_datasets_names(client: AsyncClient):
    """Seeded datasets have expected names."""
    resp = await client.get("/training-data/datasets")
    names = [d["name"] for d in resp.json()["datasets"]]
    assert "fare_training_v1" in names
    assert "demand_training_v1" in names
    assert "eta_training_v1" in names


@pytest.mark.anyio
async def test_get_dataset(client: AsyncClient):
    """Get a specific dataset by ID."""
    resp = await client.get("/training-data/datasets/ds-fare-v1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ds-fare-v1"
    assert data["name"] == "fare_training_v1"
    assert data["label_column"] == "fare_amount"
    assert data["status"] == "ready"


@pytest.mark.anyio
async def test_get_dataset_not_found(client: AsyncClient):
    """Requesting a nonexistent dataset returns 404."""
    resp = await client.get("/training-data/datasets/ds-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_dataset_has_features(client: AsyncClient):
    """Dataset spec includes feature names."""
    resp = await client.get("/training-data/datasets/ds-fare-v1")
    data = resp.json()
    assert len(data["feature_names"]) > 0
    assert "pickup_zone_id" in data["feature_names"]
    assert "trip_distance" in data["feature_names"]


@pytest.mark.anyio
async def test_get_dataset_has_split_ratio(client: AsyncClient):
    """Dataset spec includes split ratios."""
    resp = await client.get("/training-data/datasets/ds-fare-v1")
    data = resp.json()
    assert "train" in data["split_ratio"]
    assert "val" in data["split_ratio"]
    assert "test" in data["split_ratio"]


@pytest.mark.anyio
async def test_create_dataset(client: AsyncClient):
    """Create a new dataset specification."""
    body = {
        "name": "test_dataset_v1",
        "feature_names": ["zone_id", "hour", "distance"],
        "label_column": "fare",
        "date_range": {"start": "2024-02-01", "end": "2024-02-28"},
        "split_ratio": {"train": 0.8, "val": 0.1, "test": 0.1},
        "sampling_strategy": "stratified",
    }
    resp = await client.post("/training-data/datasets", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_dataset_v1"
    assert data["status"] == "draft"
    assert data["sampling_strategy"] == "stratified"


@pytest.mark.anyio
async def test_create_dataset_appears_in_list(client: AsyncClient):
    """Newly created dataset appears in the list."""
    body = {
        "name": "new_dataset",
        "feature_names": ["f1", "f2"],
        "label_column": "target",
        "date_range": {},
        "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15},
        "sampling_strategy": "random",
    }
    await client.post("/training-data/datasets", json=body)
    resp = await client.get("/training-data/datasets")
    assert resp.json()["total"] == 4


@pytest.mark.anyio
async def test_prepare_dataset(client: AsyncClient):
    """Prepare a dataset changes status to ready."""
    # Create a draft dataset first
    body = {
        "name": "prep_test",
        "feature_names": ["f1"],
        "label_column": "target",
        "date_range": {},
        "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15},
        "sampling_strategy": "random",
    }
    create_resp = await client.post("/training-data/datasets", json=body)
    ds_id = create_resp.json()["id"]

    resp = await client.post(f"/training-data/datasets/{ds_id}/prepare")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.anyio
async def test_prepare_dataset_not_found(client: AsyncClient):
    """Preparing a nonexistent dataset returns 404."""
    resp = await client.post("/training-data/datasets/ds-nonexistent/prepare")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_dataset_stats(client: AsyncClient):
    """Get statistics for a prepared dataset."""
    resp = await client.get("/training-data/datasets/ds-fare-v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 150000
    assert data["feature_count"] == 9
    assert data["missing_values_pct"] >= 0
    assert isinstance(data["label_distribution"], dict)


@pytest.mark.anyio
async def test_get_dataset_stats_not_found(client: AsyncClient):
    """Stats for nonexistent dataset returns 404."""
    resp = await client.get("/training-data/datasets/ds-nonexistent/stats")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_dataset_stats_not_prepared(client: AsyncClient):
    """Stats for a draft (unprepared) dataset returns 400."""
    body = {
        "name": "unprepared",
        "feature_names": ["f1"],
        "label_column": "target",
        "date_range": {},
        "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15},
        "sampling_strategy": "random",
    }
    create_resp = await client.post("/training-data/datasets", json=body)
    ds_id = create_resp.json()["id"]

    resp = await client.get(f"/training-data/datasets/{ds_id}/stats")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_dataset_sample(client: AsyncClient):
    """Get sample rows from a dataset."""
    resp = await client.get("/training-data/datasets/ds-fare-v1/sample")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "ds-fare-v1"
    assert data["total_sampled"] == 5
    assert len(data["rows"]) == 5
    assert len(data["columns"]) > 0


@pytest.mark.anyio
async def test_get_dataset_sample_has_label(client: AsyncClient):
    """Sample rows include the label column."""
    resp = await client.get("/training-data/datasets/ds-fare-v1/sample")
    data = resp.json()
    assert "fare_amount" in data["columns"]
    for row in data["rows"]:
        assert "fare_amount" in row


@pytest.mark.anyio
async def test_get_dataset_sample_not_found(client: AsyncClient):
    """Sample for nonexistent dataset returns 404."""
    resp = await client.get("/training-data/datasets/ds-nonexistent/sample")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_dataset_date_range(client: AsyncClient):
    """Dataset spec includes date range."""
    resp = await client.get("/training-data/datasets/ds-demand-v1")
    data = resp.json()
    assert data["date_range"]["start"] == "2024-01-01"
    assert data["date_range"]["end"] == "2024-01-31"
