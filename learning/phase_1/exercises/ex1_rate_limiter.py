"""
Exercise 1: Sliding Window Rate Limiter
=========================================

The gateway module demonstrated a Token Bucket rate limiter.
Now implement a SLIDING WINDOW rate limiter.

Sliding window tracks the exact timestamps of recent requests
within a time window (e.g., last 60 seconds).

WHY sliding window:
- More accurate than fixed window (no boundary burst issue)
- Smoother rate limiting experience for clients
- Used by Redis-based rate limiters (sorted sets)

TRADE-OFF vs token bucket:
- Uses more memory (stores each request timestamp)
- More precise but slightly more expensive to compute
"""

import time


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.

    Tracks request timestamps in a sliding time window.
    Allows up to `max_requests` within `window_seconds`.

    Example:
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        limiter.allow("client-1")  # True (1st request)
        ...
        limiter.allow("client-1")  # False after 10th request in 60s
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    def allow(self, client_id: str) -> bool:
        """
        Check if a request from client_id is allowed.

        Steps:
        1. Get the current timestamp
        2. Get (or create) the request history for this client
        3. Remove timestamps older than the window
        4. If count < max_requests, add timestamp and return True
        5. Otherwise return False
        """
        # TODO: Implement this method (~8 lines)
        raise NotImplementedError("Implement sliding window rate limiter")

    def remaining(self, client_id: str) -> int:
        """Return how many requests the client can still make in the current window."""
        # TODO: Implement this method (~4 lines)
        raise NotImplementedError("Implement remaining count")


# ── Tests ──


def test_allows_within_limit():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)
    for _ in range(5):
        assert limiter.allow("client-1") is True


def test_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0)
    for _ in range(3):
        limiter.allow("client-1")
    assert limiter.allow("client-1") is False


def test_separate_clients():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0)
    limiter.allow("client-1")
    limiter.allow("client-1")
    assert limiter.allow("client-1") is False
    assert limiter.allow("client-2") is True  # Different client


def test_remaining_count():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)
    assert limiter.remaining("client-1") == 5
    limiter.allow("client-1")
    limiter.allow("client-1")
    assert limiter.remaining("client-1") == 3
