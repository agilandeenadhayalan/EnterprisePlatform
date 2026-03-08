"""
Demo: Database Connection Patterns
====================================

Run: python -m learning.phase_1.src.m04_database_patterns.demo
"""

from .database import ConnectionPool, Repository, QueryTracker


def demo_connection_pool() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Connection Pooling               |")
    print("+------------------------------------------+\n")

    pool = ConnectionPool(min_size=2, max_size=5)
    print(f"  Initial: {pool.stats}")

    # Acquire connections
    conns = []
    for i in range(4):
        conn = pool.acquire()
        if conn:
            conns.append(conn)
            print(f"  Acquired conn-{conn.id}: {pool.stats}")

    # Release half
    for conn in conns[:2]:
        pool.release(conn)
        print(f"  Released conn-{conn.id}: {pool.stats}")


def demo_repository() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Repository Pattern               |")
    print("+------------------------------------------+\n")

    repo = Repository()
    repo.save("u1", {"name": "Alice", "role": "rider"})
    repo.save("u2", {"name": "Bob", "role": "driver"})

    user = repo.find_by_id("u1")
    print(f"  Found: {user}")

    all_users = repo.find_all()
    print(f"  All: {len(all_users)} users")
    print(f"  Queries executed: {repo.query_count}")


def demo_n_plus_one() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: N+1 Query Detection              |")
    print("+------------------------------------------+\n")

    tracker = QueryTracker()

    # Simulate N+1: load trips, then load each driver individually
    tracker.record("trips", "SELECT")  # 1 query for all trips
    for i in range(10):
        tracker.record("drivers", "SELECT")  # N queries for drivers

    issues = tracker.detect_n_plus_one(threshold=3)
    for issue in issues:
        print(f"  [WARN] {issue['table']}: queried {issue['count']} times -- {issue['issue']}")
    print(f"  [TIP] Fix: Use JOIN or WHERE id IN (...) to batch load")


def main() -> None:
    print("=" * 50)
    print("  Module 04: Database Connection Patterns")
    print("=" * 50)

    demo_connection_pool()
    demo_repository()
    demo_n_plus_one()

    print("\n[DONE] Module 04 demos complete!\n")


if __name__ == "__main__":
    main()
