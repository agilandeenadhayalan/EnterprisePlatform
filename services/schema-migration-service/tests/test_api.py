"""
Tests for the Schema Migration Service API.

Covers: migration CRUD, apply, rollback, version ordering, idempotency,
status tracking, and edge cases.
"""

import pytest
from httpx import AsyncClient


MIGRATION_V1 = {
    "version": 1,
    "name": "create_ride_events",
    "description": "Create the ride_events table",
    "sql_up": "CREATE TABLE ride_events (ride_id String, started_at DateTime) ENGINE = MergeTree() ORDER BY started_at",
    "sql_down": "DROP TABLE IF EXISTS ride_events",
}

MIGRATION_V2 = {
    "version": 2,
    "name": "add_fare_column",
    "description": "Add fare column to ride_events",
    "sql_up": "ALTER TABLE ride_events ADD COLUMN fare Float64",
    "sql_down": "ALTER TABLE ride_events DROP COLUMN fare",
}

MIGRATION_V3 = {
    "version": 3,
    "name": "create_driver_locations",
    "description": "Create the driver_locations table",
    "sql_up": "CREATE TABLE driver_locations (driver_id String, lat Float64, lng Float64, ts DateTime) ENGINE = MergeTree() ORDER BY ts",
    "sql_down": "DROP TABLE IF EXISTS driver_locations",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_migration(client: AsyncClient):
    """Create a new migration."""
    resp = await client.post("/migrations", json=MIGRATION_V1)
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == 1
    assert data["name"] == "create_ride_events"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.anyio
async def test_duplicate_version_rejected(client: AsyncClient):
    """Creating a migration with duplicate version returns 409."""
    await client.post("/migrations", json=MIGRATION_V1)
    resp = await client.post("/migrations", json={
        **MIGRATION_V1, "name": "different_name",
    })
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_list_migrations_ordered(client: AsyncClient):
    """Migrations are listed in version order."""
    await client.post("/migrations", json=MIGRATION_V3)
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)

    resp = await client.get("/migrations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    versions = [m["version"] for m in data["migrations"]]
    assert versions == [1, 2, 3]


@pytest.mark.anyio
async def test_apply_pending_migrations(client: AsyncClient):
    """Apply all pending migrations in order."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)

    resp = await client.post("/migrations/apply")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "apply"
    assert data["count"] == 2
    assert all(m["status"] == "applied" for m in data["migrations_affected"])


@pytest.mark.anyio
async def test_apply_idempotent(client: AsyncClient):
    """Applying when nothing is pending returns zero affected."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations/apply")

    # Second apply should be a no-op
    resp = await client.post("/migrations/apply")
    data = resp.json()
    assert data["count"] == 0


@pytest.mark.anyio
async def test_rollback_last(client: AsyncClient):
    """Rollback the last applied migration."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)
    await client.post("/migrations/apply")

    resp = await client.post("/migrations/rollback")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "rollback"
    assert data["count"] == 1
    assert data["migrations_affected"][0]["version"] == 2
    assert data["migrations_affected"][0]["status"] == "rolled_back"


@pytest.mark.anyio
async def test_rollback_nothing_applied(client: AsyncClient):
    """Rollback when nothing is applied returns zero affected."""
    resp = await client.post("/migrations/rollback")
    data = resp.json()
    assert data["count"] == 0
    assert data["migrations_affected"] == []


@pytest.mark.anyio
async def test_migration_status_empty(client: AsyncClient):
    """Status with no migrations."""
    resp = await client.get("/migrations/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_version"] is None
    assert data["latest_version"] is None
    assert data["total_migrations"] == 0
    assert data["pending_count"] == 0
    assert data["applied_count"] == 0


@pytest.mark.anyio
async def test_migration_status_with_pending(client: AsyncClient):
    """Status shows pending migrations."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)

    resp = await client.get("/migrations/status")
    data = resp.json()
    assert data["current_version"] is None
    assert data["latest_version"] == 2
    assert data["total_migrations"] == 2
    assert data["pending_count"] == 2
    assert data["applied_count"] == 0


@pytest.mark.anyio
async def test_migration_status_after_apply(client: AsyncClient):
    """Status after applying all migrations."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)
    await client.post("/migrations/apply")

    resp = await client.get("/migrations/status")
    data = resp.json()
    assert data["current_version"] == 2
    assert data["pending_count"] == 0
    assert data["applied_count"] == 2


@pytest.mark.anyio
async def test_migration_status_after_rollback(client: AsyncClient):
    """Status after rolling back one migration."""
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)
    await client.post("/migrations/apply")
    await client.post("/migrations/rollback")

    resp = await client.get("/migrations/status")
    data = resp.json()
    assert data["current_version"] == 1
    assert data["applied_count"] == 1


@pytest.mark.anyio
async def test_full_migration_workflow(client: AsyncClient):
    """End-to-end: create -> apply -> add more -> apply -> rollback."""
    # Create v1 and v2
    await client.post("/migrations", json=MIGRATION_V1)
    await client.post("/migrations", json=MIGRATION_V2)

    # Apply both
    resp = await client.post("/migrations/apply")
    assert resp.json()["count"] == 2

    # Add v3
    await client.post("/migrations", json=MIGRATION_V3)

    # Status shows 1 pending
    status = await client.get("/migrations/status")
    assert status.json()["pending_count"] == 1
    assert status.json()["current_version"] == 2

    # Apply v3
    resp = await client.post("/migrations/apply")
    assert resp.json()["count"] == 1

    # Rollback v3
    resp = await client.post("/migrations/rollback")
    assert resp.json()["count"] == 1
    assert resp.json()["migrations_affected"][0]["version"] == 3

    # Status: current version is 2
    status = await client.get("/migrations/status")
    assert status.json()["current_version"] == 2
    assert status.json()["applied_count"] == 2
