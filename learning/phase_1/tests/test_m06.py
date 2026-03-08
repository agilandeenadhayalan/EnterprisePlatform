"""Tests for Module 06: Containerization."""

from learning.phase_1.src.m06_containerization.containers import (
    Container,
    DockerCompose,
    ContainerState,
    HealthCheck,
)


class TestContainer:
    def test_starts_in_created_state(self):
        c = Container(name="test", image="test:latest", port=8080)
        assert c.state == ContainerState.CREATED

    def test_start_changes_state(self):
        c = Container(name="test", image="test:latest", port=8080)
        c.start()
        assert c.state == ContainerState.RUNNING


class TestDockerCompose:
    def test_dependency_order(self):
        compose = DockerCompose()
        compose.add_service(Container(
            name="app", image="app:latest", port=8080,
            depends_on=["db"],
        ))
        compose.add_service(Container(
            name="db", image="postgres:16", port=5432,
        ))

        order = compose.resolve_startup_order()
        assert order.index("db") < order.index("app")

    def test_up_starts_all(self):
        compose = DockerCompose()
        compose.add_service(Container(name="a", image="a", port=1))
        compose.add_service(Container(name="b", image="b", port=2))
        compose.up()
        assert all(
            c.state == ContainerState.RUNNING
            for c in compose.containers.values()
        )

    def test_complex_dependency_chain(self):
        compose = DockerCompose()
        compose.add_service(Container(name="gateway", image="gw", port=3000, depends_on=["auth", "user"]))
        compose.add_service(Container(name="auth", image="auth", port=8001, depends_on=["postgres", "redis"]))
        compose.add_service(Container(name="user", image="user", port=8002, depends_on=["postgres"]))
        compose.add_service(Container(name="postgres", image="pg", port=5432))
        compose.add_service(Container(name="redis", image="redis", port=6379))

        order = compose.resolve_startup_order()
        # Infra must come before services
        assert order.index("postgres") < order.index("auth")
        assert order.index("redis") < order.index("auth")
        assert order.index("auth") < order.index("gateway")
