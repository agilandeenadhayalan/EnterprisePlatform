"""Tests for Module 04: Database Connection Patterns."""

from learning.phase_1.src.m04_database_patterns.database import (
    ConnectionPool,
    Repository,
    QueryTracker,
)


class TestConnectionPool:
    def test_pre_warms_min_connections(self):
        pool = ConnectionPool(min_size=3, max_size=10)
        assert pool.stats["idle"] == 3

    def test_acquire_returns_connection(self):
        pool = ConnectionPool(min_size=2, max_size=5)
        conn = pool.acquire()
        assert conn is not None
        assert conn.is_idle is False

    def test_release_returns_to_pool(self):
        pool = ConnectionPool(min_size=2, max_size=5)
        conn = pool.acquire()
        pool.release(conn)
        assert pool.stats["idle"] == 2

    def test_exhausted_returns_none(self):
        pool = ConnectionPool(min_size=1, max_size=2)
        pool.acquire()
        pool.acquire()
        assert pool.acquire() is None


class TestRepository:
    def test_save_and_find(self):
        repo = Repository()
        repo.save("u1", {"name": "Alice"})
        found = repo.find_by_id("u1")
        assert found is not None
        assert found["name"] == "Alice"

    def test_find_nonexistent_returns_none(self):
        repo = Repository()
        assert repo.find_by_id("missing") is None

    def test_delete(self):
        repo = Repository()
        repo.save("u1", {"name": "Alice"})
        assert repo.delete("u1") is True
        assert repo.find_by_id("u1") is None


class TestQueryTracker:
    def test_detects_n_plus_one(self):
        tracker = QueryTracker()
        tracker.record("trips", "SELECT")
        for _ in range(10):
            tracker.record("drivers", "SELECT")
        issues = tracker.detect_n_plus_one(threshold=3)
        assert len(issues) > 0
        assert any(i["table"] == "drivers" for i in issues)
