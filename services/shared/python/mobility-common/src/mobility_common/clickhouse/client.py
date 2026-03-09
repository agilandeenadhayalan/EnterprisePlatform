"""
ClickHouse async client wrapper.

Wraps clickhouse-connect for consistent access patterns across all
Phase 3 services.  Falls back gracefully when ClickHouse is unavailable
(same pattern as the Kafka producer fallback).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import clickhouse_connect
    from clickhouse_connect.driver.client import Client as CHClient
    _HAS_CH = True
except ImportError:
    _HAS_CH = False


class ClickHouseClient:
    """Thin wrapper around clickhouse-connect with connection management."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        database: str = "mobility_analytics",
        user: str = "default",
        password: str = "",
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._client: CHClient | None = None
        self._connected = False

    # ── Lifecycle ──

    async def connect(self) -> None:
        """Open a ClickHouse connection (sync under the hood)."""
        if not _HAS_CH:
            logger.warning("clickhouse-connect not installed — running in mock mode")
            return
        try:
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                username=self.user,
                password=self.password,
            )
            self._connected = True
            logger.info("Connected to ClickHouse %s:%s/%s", self.host, self.port, self.database)
        except Exception as exc:
            logger.warning("ClickHouse connection failed (%s) — running in mock mode", exc)
            self._connected = False

    async def close(self) -> None:
        """Close the ClickHouse connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False
            logger.info("ClickHouse connection closed")

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    # ── Query Methods ──

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute a query and return rows as list of dicts."""
        if not self.is_connected:
            logger.debug("ClickHouse not connected — returning empty result")
            return []
        try:
            result = self._client.query(query, parameters=params or {})
            columns = result.column_names
            return [dict(zip(columns, row)) for row in result.result_rows]
        except Exception as exc:
            logger.error("ClickHouse query error: %s", exc)
            raise

    async def command(self, query: str) -> None:
        """Execute a DDL or command (no result expected)."""
        if not self.is_connected:
            logger.debug("ClickHouse not connected — skipping command")
            return
        self._client.command(query)

    async def insert_rows(
        self,
        table: str,
        rows: list[list[Any]],
        column_names: list[str],
    ) -> int:
        """Insert rows into a table.  Returns count inserted."""
        if not self.is_connected:
            logger.debug("ClickHouse not connected — skipping insert")
            return 0
        if not rows:
            return 0
        self._client.insert(table, rows, column_names=column_names)
        return len(rows)

    async def insert_dicts(self, table: str, data: list[dict[str, Any]]) -> int:
        """Insert rows from a list of dicts (auto-extracts column names)."""
        if not data:
            return 0
        columns = list(data[0].keys())
        rows = [[row.get(c) for c in columns] for row in data]
        return await self.insert_rows(table, rows, columns)

    # ── Health ──

    async def health_check(self) -> bool:
        """Return True if ClickHouse is reachable."""
        if not self.is_connected:
            return False
        try:
            result = self._client.query("SELECT 1")
            return result.result_rows[0][0] == 1
        except Exception:
            return False
