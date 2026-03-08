"""
Database Connection Patterns Simulator
=======================================

Demonstrates connection pooling, Repository pattern, and N+1 detection.
Pure Python — no actual database connections.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from collections import deque


# ── Connection Pool ──


@dataclass
class Connection:
    """Simulated database connection."""
    id: int
    is_idle: bool = True
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    query_count: int = 0


class ConnectionPool:
    """
    Database connection pool simulator.

    WHY pooling:
    - Creating a TCP connection to PostgreSQL takes ~5-10ms
    - In a service handling 1000 req/s, that's 5-10 seconds wasted per second
    - Pool maintains warm connections ready for immediate use

    SIZING RULE: pool_size = (core_count * 2) + effective_spindle_count
    For PostgreSQL on SSD: typically 10-20 connections per service instance.
    """

    def __init__(self, min_size: int = 2, max_size: int = 10) -> None:
        self.min_size = min_size
        self.max_size = max_size
        self.pool: deque[Connection] = deque()
        self.active: dict[int, Connection] = {}
        self._next_id = 0
        self._lock = threading.Lock()

        # Pre-warm minimum connections
        for _ in range(min_size):
            self._create_connection()

    def _create_connection(self) -> Connection:
        self._next_id += 1
        conn = Connection(id=self._next_id)
        self.pool.append(conn)
        return conn

    def acquire(self) -> Connection | None:
        """Get a connection from the pool."""
        with self._lock:
            # Try to get an idle connection
            if self.pool:
                conn = self.pool.popleft()
                conn.is_idle = False
                conn.last_used = time.time()
                self.active[conn.id] = conn
                return conn

            # Create new if under max
            total = len(self.active)
            if total < self.max_size:
                conn = self._create_connection()
                self.pool.popleft()  # Remove from idle pool
                conn.is_idle = False
                self.active[conn.id] = conn
                return conn

            return None  # Pool exhausted

    def release(self, conn: Connection) -> None:
        """Return a connection to the pool."""
        with self._lock:
            conn.is_idle = True
            conn.query_count += 1
            del self.active[conn.id]
            self.pool.append(conn)

    @property
    def stats(self) -> dict:
        return {
            "idle": len(self.pool),
            "active": len(self.active),
            "total": len(self.pool) + len(self.active),
            "max": self.max_size,
        }


# ── Repository Pattern ──


class Repository:
    """
    Base repository abstracting data access.

    WHY Repository pattern:
    - Decouples business logic from database queries
    - Testable: swap with in-memory implementation for tests
    - Consistent: all data access goes through a single interface

    Each service has repositories like UserRepository, TripRepository, etc.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._query_log: list[str] = []

    def save(self, entity_id: str, data: dict) -> dict:
        self._query_log.append(f"INSERT/UPDATE {entity_id}")
        self._store[entity_id] = {**data, "id": entity_id}
        return self._store[entity_id]

    def find_by_id(self, entity_id: str) -> dict | None:
        self._query_log.append(f"SELECT WHERE id={entity_id}")
        return self._store.get(entity_id)

    def find_all(self) -> list[dict]:
        self._query_log.append("SELECT ALL")
        return list(self._store.values())

    def delete(self, entity_id: str) -> bool:
        self._query_log.append(f"DELETE {entity_id}")
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    @property
    def query_count(self) -> int:
        return len(self._query_log)


# ── N+1 Query Detector ──


class QueryTracker:
    """
    Detects N+1 query patterns.

    THE PROBLEM: Loading a list of trips, then loading the driver for
    each trip individually = 1 query for trips + N queries for drivers = N+1.

    SOLUTION: Eager load with JOIN or batch SELECT WHERE id IN (...).
    """

    def __init__(self) -> None:
        self.queries: list[dict] = []

    def record(self, table: str, query_type: str, count: int = 1) -> None:
        self.queries.append({
            "table": table,
            "type": query_type,
            "count": count,
            "time": time.time(),
        })

    def detect_n_plus_one(self, threshold: int = 3) -> list[dict]:
        """Detect tables queried more than threshold times in sequence."""
        from collections import Counter
        table_counts = Counter(q["table"] for q in self.queries)
        return [
            {"table": t, "count": c, "issue": "Possible N+1 query pattern"}
            for t, c in table_counts.items()
            if c > threshold
        ]
