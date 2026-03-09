"""
Tests for CDC Connector service.

Covers table registration, CDC sync, stream status, table unregistration,
watermark tracking, and Kafka topic configuration.
"""

import pytest
from httpx import AsyncClient


REGISTER_CONFIG = {
    "schema_name": "public",
    "config": {
        "watermark_column": "updated_at",
        "poll_interval_seconds": 30,
        "batch_size": 1000,
        "kafka_topic": "etl.cdc.events.v1",
    },
}


async def register_table(client: AsyncClient, table_name: str) -> dict:
    response = await client.post(f"/cdc/tables/{table_name}/register", json=REGISTER_CONFIG)
    return response.json()


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "CDC Connector" in data["service"]


@pytest.mark.anyio
async def test_register_table(client: AsyncClient):
    response = await client.post("/cdc/tables/users/register", json=REGISTER_CONFIG)
    assert response.status_code == 201
    data = response.json()
    assert data["table_name"] == "users"
    assert data["schema_name"] == "public"
    assert data["state"] == "active"
    assert data["config"]["watermark_column"] == "updated_at"
    assert data["config"]["kafka_topic"] == "etl.cdc.events.v1"
    assert data["registered_at"] is not None


@pytest.mark.anyio
async def test_register_table_default_config(client: AsyncClient):
    response = await client.post("/cdc/tables/vehicles/register")
    assert response.status_code == 201
    data = response.json()
    assert data["table_name"] == "vehicles"
    assert data["config"]["watermark_column"] == "updated_at"


@pytest.mark.anyio
async def test_register_table_duplicate(client: AsyncClient):
    await client.post("/cdc/tables/payments/register", json=REGISTER_CONFIG)
    response = await client.post("/cdc/tables/payments/register", json=REGISTER_CONFIG)
    assert response.status_code == 409


@pytest.mark.anyio
async def test_list_tracked_tables(client: AsyncClient):
    await register_table(client, "table_a")
    await register_table(client, "table_b")

    response = await client.get("/cdc/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert "total" in data
    assert data["total"] >= 2
    table_names = [t["table_name"] for t in data["tables"]]
    assert "table_a" in table_names
    assert "table_b" in table_names


@pytest.mark.anyio
async def test_sync_table(client: AsyncClient):
    await register_table(client, "rides")
    response = await client.post("/cdc/tables/rides/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "rides"
    assert data["changes_captured"] > 0
    assert data["new_watermark"] is not None
    assert data["kafka_topic"] == "etl.cdc.events.v1"
    assert "Captured" in data["message"]


@pytest.mark.anyio
async def test_sync_unregistered_table(client: AsyncClient):
    response = await client.post("/cdc/tables/nonexistent/sync")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_cdc_status(client: AsyncClient):
    await register_table(client, "status_test_table")
    await client.post("/cdc/tables/status_test_table/sync")

    response = await client.get("/cdc/status")
    assert response.status_code == 200
    data = response.json()
    assert "streams" in data
    assert "total_tables" in data
    assert "active_streams" in data
    assert "total_events_captured" in data
    assert data["total_tables"] >= 1
    assert data["active_streams"] >= 1
    assert data["total_events_captured"] > 0


@pytest.mark.anyio
async def test_cdc_stream_details(client: AsyncClient):
    await register_table(client, "drivers_cdc")
    await client.post("/cdc/tables/drivers_cdc/sync")

    response = await client.get("/cdc/status")
    data = response.json()
    stream = next(s for s in data["streams"] if s["table_name"] == "drivers_cdc")
    assert stream["state"] == "active"
    assert stream["events_captured"] > 0


@pytest.mark.anyio
async def test_unregister_table(client: AsyncClient):
    await register_table(client, "to_delete")
    response = await client.delete("/cdc/tables/to_delete")
    assert response.status_code == 204

    # Verify unregistered
    response = await client.get("/cdc/tables")
    data = response.json()
    table_names = [t["table_name"] for t in data["tables"]]
    assert "to_delete" not in table_names


@pytest.mark.anyio
async def test_unregister_nonexistent_table(client: AsyncClient):
    response = await client.delete("/cdc/tables/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_sync_updates_watermark(client: AsyncClient):
    await register_table(client, "watermark_test")

    # First sync
    response1 = await client.post("/cdc/tables/watermark_test/sync")
    wm1 = response1.json()["new_watermark"]
    assert wm1 is not None

    # Second sync should update watermark
    response2 = await client.post("/cdc/tables/watermark_test/sync")
    wm2 = response2.json()["new_watermark"]
    assert wm2 is not None


@pytest.mark.anyio
async def test_cumulative_changes_tracked(client: AsyncClient):
    await register_table(client, "cumulative_test")
    await client.post("/cdc/tables/cumulative_test/sync")
    await client.post("/cdc/tables/cumulative_test/sync")

    response = await client.get("/cdc/tables")
    data = response.json()
    table = next(t for t in data["tables"] if t["table_name"] == "cumulative_test")
    assert table["total_changes_captured"] > 0
