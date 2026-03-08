"""
API Gateway Simulator
=====================

Demonstrates core gateway patterns without any external dependencies.
This is a pure-Python simulation — the real gateway lives in
services/gateway/api-gateway/ (TypeScript/Express).

Architecture:
    Client Request → Gateway → Route Matching → Rate Limiter → Circuit Breaker → Backend Service
"""

from __future__ import annotations

import time
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ── Route Matching ──


@dataclass
class Route:
    """A gateway route mapping a URL pattern to a backend service."""
    pattern: str               # e.g., "/api/v1/users"
    service: str               # e.g., "user-service"
    methods: list[str] = field(default_factory=lambda: ["GET"])
    version: str = "v1"
    strip_prefix: bool = True  # Remove /api/v1 before forwarding

    def matches(self, path: str, method: str = "GET") -> bool:
        """Check if a request matches this route."""
        if method.upper() not in self.methods:
            return False
        # Simple prefix matching (production gateways use regex/trie)
        return path.startswith(self.pattern)


class RouteTable:
    """
    Route table for mapping incoming requests to backend services.

    WHY: In a microservices architecture, clients don't call services directly.
    The gateway provides a single entry point and routes requests to the
    correct backend based on URL path, HTTP method, and headers.
    """

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add_route(self, pattern: str, service: str, methods: list[str] | None = None, **kwargs) -> None:
        """Register a route."""
        self.routes.append(Route(
            pattern=pattern,
            service=service,
            methods=methods or ["GET"],
            **kwargs,
        ))

    def match(self, path: str, method: str = "GET") -> Route | None:
        """Find the first matching route for a request."""
        for route in self.routes:
            if route.matches(path, method):
                return route
        return None


# ── Rate Limiter ──


class RateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class TokenBucket:
    """
    Token bucket rate limiter.

    WHY token bucket over alternatives:
    - Allows bursts (unlike fixed window)
    - Simple to implement (unlike sliding window log)
    - Memory efficient (O(1) per client, unlike sliding window)

    ALTERNATIVE: Sliding window counters are more accurate but need
    more storage. Redis-based implementations use sorted sets.
    """
    capacity: int           # Max tokens in bucket
    refill_rate: float      # Tokens added per second
    tokens: float = 0.0     # Current token count
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)

    def allow(self) -> bool:
        """Check if a request is allowed (consumes one token)."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    """Per-client rate limiter using token bucket algorithm."""

    def __init__(self, capacity: int = 60, refill_rate: float = 1.0) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def check(self, client_id: str) -> bool:
        """Check if a client's request is allowed."""
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                capacity=self.capacity,
                refill_rate=self.refill_rate,
            )
        return self.buckets[client_id].allow()


# ── Circuit Breaker ──


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation — requests pass through
    OPEN = "open"           # Failures exceeded threshold — requests fail fast
    HALF_OPEN = "half_open" # Testing recovery — one request allowed through


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for preventing cascade failures.

    WHY: When a downstream service is failing, continuing to send
    requests wastes resources and can cascade failures. The circuit
    breaker pattern "trips" after N failures and returns errors
    immediately, giving the failing service time to recover.

    State machine:
        CLOSED --[failures >= threshold]--> OPEN
        OPEN --[timeout elapsed]--> HALF_OPEN
        HALF_OPEN --[success]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
    """
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before trying again
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0

    def can_execute(self) -> bool:
        """Check if a request should be allowed through."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if enough time has passed to try again
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN: allow one request through to test
        return True

    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        self.success_count += 1

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


# ── API Gateway (Orchestrator) ──


@dataclass
class GatewayRequest:
    """Simulated HTTP request."""
    path: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    client_id: str = "anonymous"
    body: Any = None


@dataclass
class GatewayResponse:
    """Simulated HTTP response."""
    status_code: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    routed_to: str | None = None


class ApiGateway:
    """
    Simulated API Gateway combining routing, rate limiting, and circuit breaking.

    This is the central orchestrator that every request passes through.
    In production, this would be Kong, Envoy, or a custom Express/Fastify app.
    """

    def __init__(self) -> None:
        self.route_table = RouteTable()
        self.rate_limiter = RateLimiter(capacity=10, refill_rate=2.0)
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

    def register_service(self, pattern: str, service: str, methods: list[str] | None = None) -> None:
        """Register a backend service route."""
        self.route_table.add_route(pattern, service, methods or ["GET", "POST", "PUT", "DELETE"])
        self.circuit_breakers[service] = CircuitBreaker()

    def handle_request(self, request: GatewayRequest) -> GatewayResponse:
        """
        Process a request through the full gateway pipeline:
        1. Route matching
        2. Rate limiting
        3. Circuit breaker check
        4. Forward to backend (simulated)
        """
        # Step 1: Route matching
        route = self.route_table.match(request.path, request.method)
        if not route:
            return GatewayResponse(status_code=404, body={"error": "Not Found"})

        # Step 2: Rate limiting
        if not self.rate_limiter.check(request.client_id):
            return GatewayResponse(
                status_code=429,
                body={"error": "Too Many Requests"},
                headers={"Retry-After": "1"},
            )

        # Step 3: Circuit breaker
        cb = self.circuit_breakers.get(route.service)
        if cb and not cb.can_execute():
            return GatewayResponse(
                status_code=503,
                body={"error": "Service Unavailable", "circuit": "open"},
                routed_to=route.service,
            )

        # Step 4: "Forward" to backend (simulated success)
        if cb:
            cb.record_success()

        return GatewayResponse(
            status_code=200,
            body={"service": route.service, "path": request.path},
            routed_to=route.service,
        )
