"""
Tests for ETL Worker Taxi Loader service.

Covers load operations, status tracking, checkpoint management,
and specific month loading with validation.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Taxi Loader" in data["service"]


@pytest.mark.anyio
async def test_load_taxi_data(client: AsyncClient):
    response = await client.post("/load", json={"year": 2023, "month": 1, "batch_size": 100000})
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023
    assert data["month"] == 1
    assert data["state"] == "completed"
    assert data["rows_loaded"] > 0
    assert data["current_file"] == "yellow_tripdata_2023-01.parquet"


@pytest.mark.anyio
async def test_load_taxi_data_default_batch(client: AsyncClient):
    response = await client.post("/load", json={"year": 2023, "month": 6})
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "completed"


@pytest.mark.anyio
async def test_load_invalid_year(client: AsyncClient):
    response = await client.post("/load", json={"year": 2000, "month": 1})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_load_invalid_month(client: AsyncClient):
    response = await client.post("/load", json={"year": 2023, "month": 13})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_load_specific_month(client: AsyncClient):
    response = await client.post("/load/2022/7")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2022
    assert data["month"] == 7
    assert data["state"] == "completed"
    assert data["rows_loaded"] > 0


@pytest.mark.anyio
async def test_load_specific_month_invalid_year(client: AsyncClient):
    response = await client.post("/load/2000/1")
    assert response.status_code == 400


@pytest.mark.anyio
async def test_load_specific_month_invalid_month(client: AsyncClient):
    response = await client.post("/load/2023/13")
    assert response.status_code == 400


@pytest.mark.anyio
async def test_load_status(client: AsyncClient):
    await client.post("/load", json={"year": 2023, "month": 3})
    await client.post("/load", json={"year": 2023, "month": 4})

    response = await client.get("/load/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_jobs" in data
    assert "completed_jobs" in data
    assert "total_rows_loaded" in data
    assert data["completed_jobs"] >= 2
    assert data["total_rows_loaded"] > 0


@pytest.mark.anyio
async def test_load_checkpoint(client: AsyncClient):
    await client.post("/load", json={"year": 2023, "month": 5})

    response = await client.get("/load/checkpoint")
    assert response.status_code == 200
    data = response.json()
    assert "checkpoints" in data
    assert "total" in data
    assert data["total"] >= 1
    cp = next(c for c in data["checkpoints"] if c["year"] == 2023 and c["month"] == 5)
    assert cp["rows_loaded"] > 0
    assert cp["last_file"] is not None


@pytest.mark.anyio
async def test_load_speed_tracking(client: AsyncClient):
    response = await client.post("/load", json={"year": 2023, "month": 8})
    data = response.json()
    assert data["speed_rows_per_sec"] > 0


@pytest.mark.anyio
async def test_load_job_has_timestamps(client: AsyncClient):
    response = await client.post("/load", json={"year": 2023, "month": 9})
    data = response.json()
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


@pytest.mark.anyio
async def test_load_creates_correct_filename(client: AsyncClient):
    response = await client.post("/load/2024/12")
    data = response.json()
    assert data["current_file"] == "yellow_tripdata_2024-12.parquet"
