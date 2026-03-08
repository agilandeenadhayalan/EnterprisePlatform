"""
Exercise 4: Connection Pool Health Check
==========================================

Extend the connection pool with health checking:
- Periodically validate idle connections
- Remove stale connections (idle too long)
- Replace removed connections up to min_size
"""

import time
from learning.phase_1.src.m04_database_patterns.database import ConnectionPool, Connection


class HealthCheckedPool(ConnectionPool):
    """
    Connection pool with health monitoring.

    Adds:
    - max_idle_time: Remove connections idle longer than this
    - health_check(): Validate and clean up stale connections
    - stats include stale_removed count
    """

    def __init__(self, min_size: int = 2, max_size: int = 10,
                 max_idle_time: float = 300.0) -> None:
        super().__init__(min_size, max_size)
        self.max_idle_time = max_idle_time
        self.stale_removed = 0

    def health_check(self) -> dict:
        """
        Check all idle connections and remove stale ones.

        Steps:
        1. Iterate through idle connections in self.pool
        2. Remove any where (now - last_used) > max_idle_time
        3. If pool drops below min_size, create new connections
        4. Return stats dict with removed/created counts

        Returns: {"removed": int, "created": int, "pool_size": int}
        """
        # TODO: Implement health check (~12 lines)
        raise NotImplementedError("Implement connection health check")


# ── Tests ──


def test_removes_stale_connections():
    pool = HealthCheckedPool(min_size=2, max_size=5, max_idle_time=0.0)
    # All connections should be considered stale (max_idle_time=0)
    time.sleep(0.01)  # Ensure some time passes
    result = pool.health_check()
    assert result["removed"] >= 2


def test_maintains_min_size():
    pool = HealthCheckedPool(min_size=3, max_size=10, max_idle_time=0.0)
    time.sleep(0.01)
    pool.health_check()
    assert pool.stats["idle"] >= 3
