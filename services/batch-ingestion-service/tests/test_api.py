"""
Tests for Batch Ingestion Service.

Covers batch ingestion, schema validation, job status tracking,
ingestion history, and event production.
"""

import pytest
from httpx import AsyncClient


SAMPLE_INGESTION = {
    "schema_name": "taxi_trips",
    "source": "nyc-tlc-s3",
    "files": [
        {
            "filename": "yellow_tripdata_2023-01.parquet",
            "format": "parquet",
            "size_bytes": 524288000,
            "row_count": 3000000,
        },
    ],
    "target_layer": "bronze",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Batch Ingestion" in data["service"]


@pytest.mark.anyio
async def test_ingest_batch(client: AsyncClient):
    response = await client.post("/ingest", json=SAMPLE_INGESTION)
    assert response.status_code == 201
    data = response.json()
    assert data["schema_name"] == "taxi_trips"
    assert data["source"] == "nyc-tlc-s3"
    assert data["state"] == "completed"
    assert data["stats"]["files_processed"] == 1
    assert data["stats"]["total_bytes"] == 524288000
    assert data["stats"]["total_rows"] == 3000000
    assert data["minio_path"] is not None
    assert data["event_produced"] is True


@pytest.mark.anyio
async def test_ingest_multiple_files(client: AsyncClient):
    request = {
        "schema_name": "taxi_trips",
        "source": "nyc-tlc-s3",
        "files": [
            {"filename": "file1.parquet", "format": "parquet", "size_bytes": 100000, "row_count": 5000},
            {"filename": "file2.parquet", "format": "parquet", "size_bytes": 200000, "row_count": 10000},
        ],
    }
    response = await client.post("/ingest", json=request)
    assert response.status_code == 201
    data = response.json()
    assert data["stats"]["files_processed"] == 2
    assert data["stats"]["total_bytes"] == 300000
    assert data["stats"]["total_rows"] == 15000


@pytest.mark.anyio
async def test_ingest_unknown_schema(client: AsyncClient):
    request = {**SAMPLE_INGESTION, "schema_name": "nonexistent_schema"}
    response = await client.post("/ingest", json=request)
    assert response.status_code == 400
    assert "Unknown schema" in response.json()["detail"]


@pytest.mark.anyio
async def test_ingest_invalid_format(client: AsyncClient):
    request = {
        "schema_name": "taxi_trips",
        "source": "test",
        "files": [
            {"filename": "data.avro", "format": "avro", "size_bytes": 1000},
        ],
    }
    response = await client.post("/ingest", json=request)
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


@pytest.mark.anyio
async def test_ingest_empty_files_list(client: AsyncClient):
    request = {
        "schema_name": "taxi_trips",
        "source": "test",
        "files": [],
    }
    response = await client.post("/ingest", json=request)
    assert response.status_code == 422  # Validation error: min_length=1


@pytest.mark.anyio
async def test_ingestion_history(client: AsyncClient):
    await client.post("/ingest", json=SAMPLE_INGESTION)

    response = await client.get("/ingest/history")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.anyio
async def test_get_ingestion_job(client: AsyncClient):
    create_response = await client.post("/ingest", json=SAMPLE_INGESTION)
    job_id = create_response.json()["job_id"]

    response = await client.get(f"/ingest/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["schema_name"] == "taxi_trips"


@pytest.mark.anyio
async def test_get_ingestion_job_not_found(client: AsyncClient):
    response = await client.get("/ingest/nonexistent-job-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_schemas(client: AsyncClient):
    response = await client.get("/ingest/schemas")
    assert response.status_code == 200
    data = response.json()
    assert "schemas" in data
    assert "total" in data
    assert data["total"] >= 5
    schema_names = [s["name"] for s in data["schemas"]]
    assert "taxi_trips" in schema_names
    assert "weather_observations" in schema_names
    assert "ride_events" in schema_names


@pytest.mark.anyio
async def test_schema_has_required_columns(client: AsyncClient):
    response = await client.get("/ingest/schemas")
    data = response.json()
    taxi = next(s for s in data["schemas"] if s["name"] == "taxi_trips")
    assert "VendorID" in taxi["required_columns"]
    assert "total_amount" in taxi["required_columns"]
    assert "parquet" in taxi["formats"]


@pytest.mark.anyio
async def test_ingest_minio_path_format(client: AsyncClient):
    response = await client.post("/ingest", json=SAMPLE_INGESTION)
    data = response.json()
    assert data["minio_path"].startswith("s3://bronze/taxi_trips/")
