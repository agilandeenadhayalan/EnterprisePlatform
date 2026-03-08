"""
Demo: RESTful API Design
=========================

Run: python -m learning.phase_1.src.m03_rest_api_design.demo
"""

from .rest import CursorPaginator, IdempotencyStore, not_found, validation_error


def demo_cursor_pagination() -> None:
    """Demonstrate cursor-based pagination."""
    print("\n+------------------------------------------+")
    print("|   Demo: Cursor-Based Pagination          |")
    print("+------------------------------------------+\n")

    # Simulate 25 users
    users = [{"id": f"user-{i:03d}", "name": f"User {i}"} for i in range(25)]
    paginator = CursorPaginator(users, page_size=10)

    page_num = 1
    cursor = None
    while True:
        page = paginator.get_page(cursor)
        print(f"  Page {page_num}: {len(page.items)} items, "
              f"has_more={page.has_more}, cursor={page.next_cursor}")
        if not page.has_more:
            break
        cursor = page.next_cursor
        page_num += 1


def demo_idempotency() -> None:
    """Demonstrate idempotency keys for safe retries."""
    print("\n+------------------------------------------+")
    print("|   Demo: Idempotency Keys                 |")
    print("+------------------------------------------+\n")

    store = IdempotencyStore()
    call_count = 0

    def charge_payment():
        nonlocal call_count
        call_count += 1
        return {"amount": 25.50, "status": "charged", "call_number": call_count}

    key = "payment-abc-123"

    # First call: executes
    r1 = store.get_or_execute(key, charge_payment)
    print(f"  Call 1: amount=${r1['amount']}, replay={r1['_idempotent_replay']}, calls={call_count}")

    # Retry (same key): returns cached result
    r2 = store.get_or_execute(key, charge_payment)
    print(f"  Call 2: amount=${r2['amount']}, replay={r2['_idempotent_replay']}, calls={call_count}")

    # Different key: executes new
    r3 = store.get_or_execute("payment-xyz-456", charge_payment)
    print(f"  Call 3: amount=${r3['amount']}, replay={r3['_idempotent_replay']}, calls={call_count}")

    print(f"\n  [*] Total actual charges: {call_count} (not 3!)")


def demo_error_format() -> None:
    """Demonstrate RFC 7807 Problem Details error format."""
    print("\n+------------------------------------------+")
    print("|   Demo: RFC 7807 Error Format            |")
    print("+------------------------------------------+\n")

    errors = [
        not_found("trip", "trip-999"),
        validation_error("email", "must be a valid email address"),
    ]

    for err in errors:
        d = err.to_dict()
        print(f"  {d['status']} {d['title']}: {d['detail']}")


def main() -> None:
    print("=" * 50)
    print("  Module 03: RESTful API Design")
    print("=" * 50)

    demo_cursor_pagination()
    demo_idempotency()
    demo_error_format()

    print("\n[DONE] Module 03 demos complete!\n")


if __name__ == "__main__":
    main()
