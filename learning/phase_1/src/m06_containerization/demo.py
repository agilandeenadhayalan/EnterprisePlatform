"""
Demo: Containerization Patterns
================================

Run: python -m learning.phase_1.src.m06_containerization.demo
"""

from .containers import Container, DockerCompose, HealthCheck


def demo_compose_orchestration() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Docker Compose Orchestration     |")
    print("+------------------------------------------+\n")

    compose = DockerCompose()

    # Define Phase 1 infrastructure
    compose.add_service(Container(
        name="postgres",
        image="postgres:16-alpine",
        port=5433,
        health_check=HealthCheck(endpoint="pg_isready"),
        memory_limit="1g",
    ))

    compose.add_service(Container(
        name="redis",
        image="redis:7-alpine",
        port=6380,
        health_check=HealthCheck(endpoint="redis-cli ping"),
        memory_limit="256m",
    ))

    compose.add_service(Container(
        name="auth-service",
        image="mobility/auth-service:latest",
        port=8001,
        depends_on=["postgres", "redis"],
        environment={"DATABASE_URL": "postgresql://..."},
    ))

    compose.add_service(Container(
        name="user-service",
        image="mobility/user-service:latest",
        port=8002,
        depends_on=["postgres"],
    ))

    compose.add_service(Container(
        name="api-gateway",
        image="mobility/api-gateway:latest",
        port=3000,
        depends_on=["auth-service", "user-service"],
    ))

    # Start in dependency order
    order = compose.up()

    print("  Startup order (dependency-resolved):")
    for i, name in enumerate(order, 1):
        c = compose.containers[name]
        deps = f" (depends on: {', '.join(c.depends_on)})" if c.depends_on else ""
        print(f"  {i}. {name}:{c.port} [{c.state.value}]{deps}")


def demo_health_checks() -> None:
    print("\n+------------------------------------------+")
    print("|   Demo: Container Health Checks          |")
    print("+------------------------------------------+\n")

    services = [
        ("postgres", HealthCheck(endpoint="pg_isready", interval_seconds=10)),
        ("redis", HealthCheck(endpoint="redis-cli ping", interval_seconds=5)),
        ("auth-service", HealthCheck(endpoint="GET /health", interval_seconds=15)),
        ("api-gateway", HealthCheck(endpoint="GET /health", interval_seconds=10)),
    ]

    for name, hc in services:
        print(f"  {name}:")
        print(f"    Check: {hc.endpoint}")
        print(f"    Interval: {hc.interval_seconds}s, Timeout: {hc.timeout_seconds}s")
        print(f"    Retries: {hc.retries}, Start period: {hc.start_period}s")


def main() -> None:
    print("=" * 50)
    print("  Module 06: Containerization")
    print("=" * 50)

    demo_compose_orchestration()
    demo_health_checks()

    print("\n[DONE] Module 06 demos complete!\n")


if __name__ == "__main__":
    main()
