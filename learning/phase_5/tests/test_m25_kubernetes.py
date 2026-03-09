"""
Tests for M25: Kubernetes Fundamentals — Pod specs, deployments, services,
and ingress routing.
"""

import pytest

from m25_kubernetes.pod_spec import (
    PodStatus,
    ResourceRequirements,
    Container,
    PodSpec,
    PodLifecycle,
)
from m25_kubernetes.deployment_controller import ReplicaSet, DeploymentController
from m25_kubernetes.service_discovery import (
    ServiceType,
    Endpoint,
    KubernetesService,
    ServiceDiscovery,
)
from m25_kubernetes.ingress_routing import IngressPath, IngressRule, IngressController


# ── PodSpec & Container ──


class TestResourceRequirements:
    def test_fits_within_true(self):
        """Requests that fit within limits should return True."""
        req = ResourceRequirements(cpu_millicores=100, memory_mb=256)
        lim = ResourceRequirements(cpu_millicores=200, memory_mb=512)
        assert req.fits_within(lim) is True

    def test_fits_within_exact(self):
        """Requests equal to limits should fit."""
        req = ResourceRequirements(cpu_millicores=200, memory_mb=512)
        lim = ResourceRequirements(cpu_millicores=200, memory_mb=512)
        assert req.fits_within(lim) is True

    def test_fits_within_false_cpu(self):
        """Requests exceeding CPU limit should not fit."""
        req = ResourceRequirements(cpu_millicores=300, memory_mb=256)
        lim = ResourceRequirements(cpu_millicores=200, memory_mb=512)
        assert req.fits_within(lim) is False

    def test_fits_within_false_memory(self):
        """Requests exceeding memory limit should not fit."""
        req = ResourceRequirements(cpu_millicores=100, memory_mb=1024)
        lim = ResourceRequirements(cpu_millicores=200, memory_mb=512)
        assert req.fits_within(lim) is False

    def test_negative_values_raise(self):
        with pytest.raises(ValueError):
            ResourceRequirements(cpu_millicores=-1, memory_mb=256)


class TestContainer:
    def test_create_basic(self):
        c = Container(name="web", image="nginx:1.21")
        assert c.name == "web"
        assert c.image == "nginx:1.21"
        assert c.ports == []
        assert c.env == {}

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            Container(name="", image="nginx")

    def test_resource_limits_below_requests_raises(self):
        """Limits must be >= requests for both CPU and memory."""
        req = ResourceRequirements(cpu_millicores=500, memory_mb=512)
        lim = ResourceRequirements(cpu_millicores=250, memory_mb=256)
        with pytest.raises(ValueError, match="resource_limits must be >= resource_requests"):
            Container(
                name="app",
                image="myapp:1.0",
                resource_requests=req,
                resource_limits=lim,
            )

    def test_valid_resources_accepted(self):
        req = ResourceRequirements(cpu_millicores=100, memory_mb=128)
        lim = ResourceRequirements(cpu_millicores=200, memory_mb=256)
        c = Container(name="app", image="myapp:1.0", resource_requests=req, resource_limits=lim)
        assert c.resource_requests.cpu_millicores == 100
        assert c.resource_limits.cpu_millicores == 200


class TestPodSpec:
    def _make_container(self, name="web", ports=None):
        return Container(name=name, image="nginx:1.21", ports=ports or [])

    def test_create_pod(self):
        pod = PodSpec(name="my-pod", containers=[self._make_container()])
        assert pod.name == "my-pod"
        assert pod.namespace == "default"
        assert len(pod.containers) == 1
        assert pod.restart_policy == "Always"

    def test_no_containers_raises(self):
        with pytest.raises(ValueError, match="at least one container"):
            PodSpec(name="empty-pod", containers=[])

    def test_duplicate_container_names_raises(self):
        with pytest.raises(ValueError, match="duplicate container names"):
            PodSpec(
                name="dup-pod",
                containers=[
                    self._make_container("web"),
                    self._make_container("web"),
                ],
            )

    def test_port_conflict_across_containers_raises(self):
        with pytest.raises(ValueError, match="port 80"):
            PodSpec(
                name="port-conflict",
                containers=[
                    self._make_container("web", ports=[80]),
                    self._make_container("api", ports=[80]),
                ],
            )

    def test_multiple_containers_no_conflict(self):
        pod = PodSpec(
            name="multi",
            containers=[
                self._make_container("web", ports=[80]),
                self._make_container("api", ports=[8080]),
            ],
        )
        assert len(pod.containers) == 2

    def test_custom_namespace(self):
        pod = PodSpec(
            name="ns-pod",
            namespace="production",
            containers=[self._make_container()],
        )
        assert pod.namespace == "production"


class TestPodLifecycle:
    def test_initial_state_is_pending(self):
        lc = PodLifecycle("my-pod")
        assert lc.status == PodStatus.PENDING

    def test_schedule_stays_pending(self):
        lc = PodLifecycle("my-pod")
        lc.schedule()
        assert lc.status == PodStatus.PENDING
        assert lc.scheduled is True

    def test_pending_to_running(self):
        lc = PodLifecycle("my-pod")
        lc.start()
        assert lc.status == PodStatus.RUNNING

    def test_running_to_succeeded(self):
        lc = PodLifecycle("my-pod")
        lc.start()
        lc.succeed()
        assert lc.status == PodStatus.SUCCEEDED

    def test_running_to_failed(self):
        lc = PodLifecycle("my-pod")
        lc.start()
        lc.fail()
        assert lc.status == PodStatus.FAILED

    def test_pending_to_succeeded_raises(self):
        lc = PodLifecycle("my-pod")
        with pytest.raises(ValueError, match="must be RUNNING"):
            lc.succeed()

    def test_pending_to_failed_raises(self):
        lc = PodLifecycle("my-pod")
        with pytest.raises(ValueError, match="must be RUNNING"):
            lc.fail()

    def test_succeeded_to_running_raises(self):
        lc = PodLifecycle("my-pod")
        lc.start()
        lc.succeed()
        with pytest.raises(ValueError, match="must be PENDING"):
            lc.start()

    def test_double_start_raises(self):
        lc = PodLifecycle("my-pod")
        lc.start()
        with pytest.raises(ValueError, match="must be PENDING"):
            lc.start()


# ── DeploymentController ──


class TestDeploymentController:
    def _make_pod_template(self, name="app-pod"):
        return PodSpec(
            name=name,
            containers=[Container(name="app", image="myapp:1.0")],
        )

    def test_initial_state(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        assert dc.replicas == 3
        rs = dc.active_replica_set
        assert rs.current_replicas == 3
        assert rs.desired_replicas == 3
        assert rs.revision == 1

    def test_scale_up(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        dc.scale(5)
        assert dc.active_replica_set.desired_replicas == 5

    def test_scale_down(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        dc.scale(1)
        assert dc.active_replica_set.desired_replicas == 1

    def test_reconcile_scale_up_limited_by_surge(self):
        dc = DeploymentController(
            name="my-deploy",
            replicas=3,
            pod_template=self._make_pod_template(),
            max_surge=2,
        )
        dc.scale(10)
        current, desired = dc.reconcile()
        # Started at 3, max_surge=2, so should add 2 -> 5
        assert current == 5
        assert desired == 10

    def test_reconcile_scale_down(self):
        dc = DeploymentController(
            name="my-deploy",
            replicas=5,
            pod_template=self._make_pod_template(),
            max_unavailable=2,
        )
        dc.scale(1)
        current, desired = dc.reconcile()
        # Started at 5, max_unavailable=2, should remove 2 -> 3
        assert current == 3
        assert desired == 1

    def test_reconcile_converges(self):
        dc = DeploymentController(
            name="my-deploy",
            replicas=3,
            pod_template=self._make_pod_template(),
            max_surge=1,
        )
        dc.scale(6)
        # Reconcile until converged
        for _ in range(10):
            current, desired = dc.reconcile()
            if current == desired:
                break
        assert current == 6

    def test_rolling_update_creates_new_revision(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        new_template = self._make_pod_template("app-pod-v2")
        new_rs = dc.update(new_template)
        assert new_rs.revision == 2
        assert dc.get_revision_history() == [1, 2]

    def test_rollback_to_previous(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        original_template = dc.pod_template
        new_template = self._make_pod_template("app-pod-v2")
        dc.update(new_template)
        rollback_rs = dc.rollback()
        assert rollback_rs.pod_template.name == original_template.name
        assert rollback_rs.revision == 3

    def test_revision_history(self):
        dc = DeploymentController(
            name="my-deploy", replicas=3, pod_template=self._make_pod_template()
        )
        dc.update(self._make_pod_template("v2"))
        dc.update(self._make_pod_template("v3"))
        assert dc.get_revision_history() == [1, 2, 3]


# ── ServiceDiscovery ──


class TestKubernetesService:
    def test_selector_matches_pod(self):
        svc = KubernetesService(
            name="web-svc",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        assert svc.matches_pod({"app": "web", "version": "v1"}) is True

    def test_selector_no_match(self):
        svc = KubernetesService(
            name="web-svc",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        assert svc.matches_pod({"app": "api"}) is False

    def test_resolve_multiple_pods(self):
        svc = KubernetesService(
            name="web-svc",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        pods = [
            {"labels": {"app": "web"}, "ip": "10.0.0.1"},
            {"labels": {"app": "web"}, "ip": "10.0.0.2"},
            {"labels": {"app": "api"}, "ip": "10.0.0.3"},
        ]
        endpoints = svc.resolve(pods)
        assert len(endpoints) == 2
        ips = {ep.ip for ep in endpoints}
        assert ips == {"10.0.0.1", "10.0.0.2"}

    def test_resolve_uses_target_port(self):
        svc = KubernetesService(
            name="web-svc",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 3000}],
        )
        pods = [{"labels": {"app": "web"}, "ip": "10.0.0.1"}]
        endpoints = svc.resolve(pods)
        assert endpoints[0].port == 3000


class TestServiceDiscovery:
    def test_register_and_resolve(self):
        sd = ServiceDiscovery()
        svc = KubernetesService(
            name="web",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        sd.register_service(svc)
        sd.register_pod("pod-1", {"app": "web"}, "10.0.0.1")
        sd.register_pod("pod-2", {"app": "web"}, "10.0.0.2")

        endpoints = sd.resolve("web")
        assert len(endpoints) == 2

    def test_resolve_no_match(self):
        sd = ServiceDiscovery()
        svc = KubernetesService(
            name="web",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        sd.register_service(svc)
        sd.register_pod("pod-1", {"app": "api"}, "10.0.0.1")

        endpoints = sd.resolve("web")
        assert len(endpoints) == 0

    def test_deregister_pod(self):
        sd = ServiceDiscovery()
        svc = KubernetesService(
            name="web",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        sd.register_service(svc)
        sd.register_pod("pod-1", {"app": "web"}, "10.0.0.1")
        sd.deregister_pod("pod-1")

        endpoints = sd.resolve("web")
        assert len(endpoints) == 0

    def test_load_balance_round_robin(self):
        sd = ServiceDiscovery()
        svc = KubernetesService(
            name="web",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        sd.register_service(svc)
        sd.register_pod("pod-1", {"app": "web"}, "10.0.0.1")
        sd.register_pod("pod-2", {"app": "web"}, "10.0.0.2")

        ep1 = sd.load_balance("web", "round-robin")
        ep2 = sd.load_balance("web", "round-robin")
        # Should alternate between the two endpoints
        assert ep1.ip != ep2.ip

    def test_load_balance_no_endpoints_raises(self):
        sd = ServiceDiscovery()
        svc = KubernetesService(
            name="web",
            service_type=ServiceType.CLUSTER_IP,
            selector={"app": "web"},
            ports=[{"name": "http", "port": 80, "target_port": 8080}],
        )
        sd.register_service(svc)
        with pytest.raises(RuntimeError, match="No ready endpoints"):
            sd.load_balance("web")

    def test_resolve_unknown_service_raises(self):
        sd = ServiceDiscovery()
        with pytest.raises(KeyError, match="not found"):
            sd.resolve("nonexistent")


# ── IngressController ──


class TestIngressController:
    def test_exact_match_priority(self):
        """Exact match should win over prefix match for the same path."""
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[
                    IngressPath("/api", "Prefix", "api-svc", 80),
                    IngressPath("/api", "Exact", "api-exact-svc", 8080),
                ],
            )
        )
        result = ic.route_request("example.com", "/api")
        assert result == ("api-exact-svc", 8080)

    def test_prefix_match(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[IngressPath("/api", "Prefix", "api-svc", 80)],
            )
        )
        result = ic.route_request("example.com", "/api/v1/users")
        assert result == ("api-svc", 80)

    def test_longest_prefix_wins(self):
        """The more specific prefix should win over a shorter one."""
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[
                    IngressPath("/api", "Prefix", "api-generic", 80),
                    IngressPath("/api/v2", "Prefix", "api-v2", 8080),
                ],
            )
        )
        result = ic.route_request("example.com", "/api/v2/users")
        assert result == ("api-v2", 8080)

    def test_no_match_returns_none(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[IngressPath("/api", "Prefix", "api-svc", 80)],
            )
        )
        result = ic.route_request("other.com", "/api")
        assert result is None

    def test_no_path_match_returns_none(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[IngressPath("/api", "Exact", "api-svc", 80)],
            )
        )
        result = ic.route_request("example.com", "/web")
        assert result is None

    def test_tls_configured(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="secure.example.com",
                paths=[IngressPath("/", "Prefix", "web-svc", 443)],
                tls_secret="tls-cert",
            )
        )
        assert ic.is_tls("secure.example.com") is True

    def test_tls_not_configured(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="plain.example.com",
                paths=[IngressPath("/", "Prefix", "web-svc", 80)],
            )
        )
        assert ic.is_tls("plain.example.com") is False

    def test_get_backends(self):
        ic = IngressController()
        ic.add_rule(
            IngressRule(
                host="example.com",
                paths=[
                    IngressPath("/api", "Prefix", "api-svc", 80),
                    IngressPath("/web", "Prefix", "web-svc", 8080),
                ],
            )
        )
        ic.add_rule(
            IngressRule(
                host="other.com",
                paths=[IngressPath("/", "Prefix", "api-svc", 80)],
            )
        )
        backends = ic.get_backends()
        assert backends == {("api-svc", 80), ("web-svc", 8080)}
