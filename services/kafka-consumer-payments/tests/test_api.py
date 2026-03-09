"""
Tests for the kafka-consumer-payments API.

Tests payment event processing, dual-write (MinIO + ClickHouse), and stats.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -- Health check --


@pytest.mark.anyio
async def test_health_check(client):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# -- POST /process --


@pytest.mark.anyio
async def test_process_single_payment(client, sample_payment_event):
    """Process a single payment event with dual write."""
    resp = await client.post("/process", json={"events": [sample_payment_event]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 1
    assert data["failed"] == 0
    assert data["clickhouse_written"] == 1
    assert data["minio_archived"] == 1


@pytest.mark.anyio
async def test_process_batch_payments(client, sample_payment_events):
    """Process a batch of payment events."""
    resp = await client.post("/process", json={"events": sample_payment_events})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 2
    assert data["clickhouse_written"] == 2
    assert data["minio_archived"] == 2


@pytest.mark.anyio
async def test_process_empty_batch(client):
    """Empty batch processes zero events."""
    resp = await client.post("/process", json={"events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["failed"] == 0


@pytest.mark.anyio
async def test_process_invalid_event(client):
    """Invalid events are counted as failures."""
    resp = await client.post("/process", json={"events": [{"bad": "data"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["failed"] == 1


@pytest.mark.anyio
async def test_process_total_amount_calculation(client, sample_payment_event):
    """Total amount = amount + tip."""
    resp = await client.post("/process", json={"events": [sample_payment_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["total_amount"] == 30.50  # 25.50 + 5.00


@pytest.mark.anyio
async def test_process_payment_fields(client, sample_payment_event):
    """Payment fields are preserved in output."""
    resp = await client.post("/process", json={"events": [sample_payment_event]})
    data = resp.json()
    result = data["results"][0]
    assert result["payment_id"] == "pay-001"
    assert result["ride_id"] == "ride-001"
    assert result["payment_method"] == "card"
    assert result["status"] == "completed"


@pytest.mark.anyio
async def test_process_mixed_valid_invalid(client, sample_payment_event):
    """Batch with mixed valid and invalid events."""
    resp = await client.post("/process", json={
        "events": [sample_payment_event, {"invalid": True}]
    })
    data = resp.json()
    assert data["processed"] == 1
    assert data["failed"] == 1


# -- GET /process/stats --


@pytest.mark.anyio
async def test_stats_initial(client):
    """Stats start at zero."""
    resp = await client.get("/process/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events_processed"] == 0
    assert data["clickhouse_writes"] == 0
    assert data["minio_writes"] == 0


@pytest.mark.anyio
async def test_stats_after_processing(client, sample_payment_events):
    """Stats update after processing."""
    await client.post("/process", json={"events": sample_payment_events})
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["events_processed"] == 2
    assert data["clickhouse_writes"] == 2
    assert data["minio_writes"] == 2
    assert data["total_amount_processed"] == 51.50  # (25.50+5.00) + (18.00+3.00)
    assert data["last_processed_at"] is not None


@pytest.mark.anyio
async def test_stats_error_tracking(client):
    """Errors are tracked in stats."""
    await client.post("/process", json={"events": [{"bad": "event"}]})
    resp = await client.get("/process/stats")
    data = resp.json()
    assert data["events_failed"] == 1
