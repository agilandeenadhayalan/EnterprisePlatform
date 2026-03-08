"""Tests for Module 01: API Gateway Patterns."""

from learning.phase_1.src.m01_api_gateway.gateway import (
    ApiGateway,
    GatewayRequest,
    RouteTable,
    RateLimiter,
    CircuitBreaker,
    CircuitState,
)


class TestRouteTable:
    def test_match_existing_route(self):
        rt = RouteTable()
        rt.add_route("/api/v1/users", "user-service", ["GET"])
        route = rt.match("/api/v1/users", "GET")
        assert route is not None
        assert route.service == "user-service"

    def test_no_match_returns_none(self):
        rt = RouteTable()
        rt.add_route("/api/v1/users", "user-service", ["GET"])
        assert rt.match("/api/v1/unknown", "GET") is None

    def test_method_filtering(self):
        rt = RouteTable()
        rt.add_route("/api/v1/users", "user-service", ["GET"])
        assert rt.match("/api/v1/users", "DELETE") is None


class TestRateLimiter:
    def test_allows_within_capacity(self):
        limiter = RateLimiter(capacity=5, refill_rate=0.0)
        results = [limiter.check("client-1") for _ in range(5)]
        assert all(results)

    def test_blocks_over_capacity(self):
        limiter = RateLimiter(capacity=3, refill_rate=0.0)
        results = [limiter.check("client-1") for _ in range(5)]
        assert results == [True, True, True, False, False]

    def test_separate_buckets_per_client(self):
        limiter = RateLimiter(capacity=2, refill_rate=0.0)
        assert limiter.check("client-1") is True
        assert limiter.check("client-2") is True  # Different client


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_requests(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=9999)
        cb.record_failure()
        assert cb.can_execute() is False

    def test_half_open_on_success_closes(self):
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


class TestApiGateway:
    def test_routes_to_correct_service(self):
        gw = ApiGateway()
        gw.register_service("/api/v1/users", "user-service")
        resp = gw.handle_request(GatewayRequest(path="/api/v1/users"))
        assert resp.status_code == 200
        assert resp.routed_to == "user-service"

    def test_404_for_unknown_route(self):
        gw = ApiGateway()
        resp = gw.handle_request(GatewayRequest(path="/unknown"))
        assert resp.status_code == 404
