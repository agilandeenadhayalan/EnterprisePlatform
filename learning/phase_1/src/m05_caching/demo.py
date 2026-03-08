"""
Demo: Caching Strategies
=========================

Run: python -m learning.phase_1.src.m05_caching.demo
"""

from .cache import CacheAside, WriteThrough


def demo_cache_aside() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Cache-Aside Pattern              |")
    print("+------------------------------------------+\n")

    cache = CacheAside(default_ttl=60.0)
    db_calls = 0

    def load_user(user_id: str):
        nonlocal db_calls
        db_calls += 1
        return {"id": user_id, "name": f"User-{user_id}", "role": "rider"}

    # First access: cache miss, loads from "DB"
    user = cache.get_or_load("user:123", lambda: load_user("123"))
    print(f"  1st access: {user['name']}, DB calls: {db_calls}")

    # Second access: cache hit
    user = cache.get_or_load("user:123", lambda: load_user("123"))
    print(f"  2nd access: {user['name']}, DB calls: {db_calls}")

    # Different user: cache miss
    user = cache.get_or_load("user:456", lambda: load_user("456"))
    print(f"  3rd access: {user['name']}, DB calls: {db_calls}")

    print(f"\n  Hit rate: {cache.hit_rate:.0%}")
    print(f"  Stats: {cache.stats}")


def demo_write_through() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Write-Through Cache              |")
    print("+------------------------------------------+\n")

    cache = WriteThrough(default_ttl=60.0)
    db = {}

    def db_write(key, value):
        db[key] = value

    # Write goes to both cache and DB
    cache.write("user:123", {"name": "Alice", "updated": True}, db_write)
    print(f"  After write:")
    print(f"    Cache: {cache.get('user:123')}")
    print(f"    DB:    {db.get('user:123')}")

    # Read hits cache immediately (no DB call needed)
    cached = cache.get("user:123")
    print(f"  Cache hit: {cached is not None}")


def main() -> None:
    print("=" * 50)
    print("  Module 05: Caching Strategies")
    print("=" * 50)

    demo_cache_aside()
    demo_write_through()

    print("\n[DONE] Module 05 demos complete!\n")


if __name__ == "__main__":
    main()
