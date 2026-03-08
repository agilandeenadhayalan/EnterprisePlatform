"""
Demo: API Gateway Patterns
===========================

Run: python -m learning.phase_1.src.m01_api_gateway.demo
"""

from .gateway import (
    ApiGateway,
    GatewayRequest,
    CircuitState,
)


def demo_routing() -> None:
    """Demonstrate request routing to backend services."""
    print("\n+------------------------------------------+")
    print("|   Demo: API Gateway Request Routing      |")
    print("+------------------------------------------+\n")

    gw = ApiGateway()

    # Register services (like configuring Kong or Envoy routes)
    gw.register_service("/api/v1/users", "user-service")
    gw.register_service("/api/v1/auth", "auth-service")
    gw.register_service("/api/v1/trips", "trip-service")
    gw.register_service("/api/v1/drivers", "driver-service")

    # Simulate requests
    requests = [
        GatewayRequest(path="/api/v1/users", method="GET", client_id="client-1"),
        GatewayRequest(path="/api/v1/auth/login", method="POST", client_id="client-1"),
        GatewayRequest(path="/api/v1/trips/123", method="GET", client_id="client-2"),
        GatewayRequest(path="/api/v1/unknown", method="GET", client_id="client-1"),
    ]

    for req in requests:
        resp = gw.handle_request(req)
        status = "[OK]" if resp.status_code == 200 else "[FAIL]"
        print(f"  {status} {req.method} {req.path} -> {resp.status_code} (routed to: {resp.routed_to or 'none'})")


def demo_rate_limiting() -> None:
    """Demonstrate rate limiting with token bucket."""
    print("\n+------------------------------------------+")
    print("|   Demo: Rate Limiting (Token Bucket)     |")
    print("+------------------------------------------+\n")

    gw = ApiGateway()
    gw.register_service("/api/v1/users", "user-service")

    # Send 15 rapid requests (capacity=10, so ~5 should be rate limited)
    allowed = 0
    limited = 0
    for i in range(15):
        req = GatewayRequest(path="/api/v1/users", client_id="spammer")
        resp = gw.handle_request(req)
        if resp.status_code == 200:
            allowed += 1
        elif resp.status_code == 429:
            limited += 1

    print(f"  Sent 15 rapid requests:")
    print(f"  [OK] Allowed: {allowed}")
    print(f"  [FAIL] Rate limited (429): {limited}")
    print(f"  Bucket capacity: 10 tokens, refill: 2/sec")


def demo_circuit_breaker() -> None:
    """Demonstrate circuit breaker state transitions."""
    print("\n+------------------------------------------+")
    print("|   Demo: Circuit Breaker State Machine    |")
    print("+------------------------------------------+\n")

    gw = ApiGateway()
    gw.register_service("/api/v1/users", "user-service")

    cb = gw.circuit_breakers["user-service"]
    print(f"  Initial state: {cb.state.value}")

    # Simulate 5 failures to trip the circuit
    for i in range(5):
        cb.record_failure()
        print(f"  Failure {i+1}: state={cb.state.value}, failures={cb.failure_count}")

    print(f"\n  Circuit is now OPEN -- requests will fail fast!")

    req = GatewayRequest(path="/api/v1/users", client_id="client-1")
    resp = gw.handle_request(req)
    print(f"  Request result: {resp.status_code} ({resp.body})")

    # Simulate recovery
    cb.state = CircuitState.HALF_OPEN
    print(f"\n  After timeout: state={cb.state.value} (testing recovery)")
    cb.record_success()
    print(f"  Success recorded: state={cb.state.value}")


def main() -> None:
    print("=" * 50)
    print("  Module 01: API Gateway Patterns")
    print("=" * 50)

    demo_routing()
    demo_rate_limiting()
    demo_circuit_breaker()

    print("\n[DONE] Module 01 demos complete!\n")


if __name__ == "__main__":
    main()
