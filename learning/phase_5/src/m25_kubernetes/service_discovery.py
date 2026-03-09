"""
Service Discovery — finding and load-balancing across Pods.

WHY THIS MATTERS:
Pods are ephemeral: they can be created, destroyed, and rescheduled at any
time, getting new IP addresses each time. Services provide a stable
virtual IP and DNS name that routes to the current set of healthy Pods.
This decouples consumers from the constantly-changing Pod topology.

Service Types:
  - ClusterIP: internal-only virtual IP (default). Accessible only inside
    the cluster. Used for inter-service communication.
  - NodePort: exposes a port on every node's IP. Useful for dev/testing.
  - LoadBalancer: provisions a cloud load balancer. Used for external traffic.
  - ExternalName: alias to an external DNS name (no proxying).

The selector-based matching is key: a Service selects Pods by labels,
not by name. This allows Deployments to roll out new Pods seamlessly
while the Service automatically picks up the new instances.
"""

from enum import Enum


class ServiceType(Enum):
    """Kubernetes Service types controlling how the service is exposed."""

    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"


class Endpoint:
    """A single endpoint (Pod IP + port) behind a Service.

    In real Kubernetes, the Endpoints controller watches Pods matching
    the Service selector and maintains this list automatically.

    Attributes:
        ip: Pod's IP address.
        port: The target port the Pod is listening on.
        is_ready: Whether the Pod's readiness probe is passing.
    """

    def __init__(self, ip: str, port: int, is_ready: bool = True):
        self.ip = ip
        self.port = port
        self.is_ready = is_ready

    def __repr__(self) -> str:
        ready = "ready" if self.is_ready else "not-ready"
        return f"Endpoint({self.ip}:{self.port}, {ready})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Endpoint):
            return NotImplemented
        return self.ip == other.ip and self.port == other.port


class KubernetesService:
    """A Kubernetes Service that routes traffic to matching Pods.

    The Service uses label selectors to find Pods. Every label in the
    selector must match a Pod's labels for the Pod to receive traffic.

    Ports configuration maps a service port (what clients connect to)
    to a target port (what the Pod listens on). This indirection allows
    the service to present a stable port even if Pod ports change.
    """

    _ip_counter = 0

    def __init__(
        self,
        name: str,
        service_type: ServiceType,
        selector: dict[str, str],
        ports: list[dict],
    ):
        self.name = name
        self.service_type = service_type
        self.selector = selector
        self.ports = ports  # [{"name": "http", "port": 80, "target_port": 8080}]

        # Auto-generate a cluster IP
        KubernetesService._ip_counter += 1
        self.cluster_ip = f"10.96.0.{KubernetesService._ip_counter}"

    def matches_pod(self, pod_labels: dict[str, str]) -> bool:
        """Check if a Pod's labels match this Service's selector.

        ALL selector labels must be present in the Pod's labels with
        matching values. The Pod may have additional labels.

        This is how Kubernetes achieves loose coupling: any Pod with
        the right labels automatically gets traffic from the Service.
        """
        for key, value in self.selector.items():
            if pod_labels.get(key) != value:
                return False
        return True

    def resolve(self, pods: list[dict]) -> list[Endpoint]:
        """Resolve this Service to a list of Endpoints.

        Args:
            pods: List of dicts with keys "labels", "ip", and optionally
                  "is_ready" (defaults to True).

        Returns:
            List of Endpoint objects for Pods matching the selector.
        """
        endpoints = []
        for pod in pods:
            if self.matches_pod(pod.get("labels", {})):
                is_ready = pod.get("is_ready", True)
                for port_config in self.ports:
                    target_port = port_config.get("target_port", port_config["port"])
                    endpoints.append(
                        Endpoint(ip=pod["ip"], port=target_port, is_ready=is_ready)
                    )
        return endpoints

    def __repr__(self) -> str:
        return (
            f"KubernetesService(name='{self.name}', type={self.service_type.value}, "
            f"ip={self.cluster_ip})"
        )


class ServiceDiscovery:
    """Registry that maps service names to live Pod endpoints.

    In real Kubernetes, kube-proxy and CoreDNS work together to provide
    service discovery. kube-proxy maintains iptables/IPVS rules that
    route traffic, while CoreDNS resolves service names to ClusterIPs.

    This class models the resolution and load-balancing behavior.

    Load balancing algorithms:
      - round-robin: distribute requests evenly in order.
      - random: pick a random endpoint each time.
    """

    def __init__(self):
        self._services: dict[str, KubernetesService] = {}
        self._pods: dict[str, dict] = {}  # name -> {labels, ip, is_ready}
        self._rr_counters: dict[str, int] = {}  # round-robin state per service

    def register_service(self, service: KubernetesService) -> None:
        """Register a Service in the discovery registry."""
        self._services[service.name] = service

    def register_pod(
        self,
        pod_name: str,
        labels: dict[str, str],
        ip: str,
        is_ready: bool = True,
    ) -> None:
        """Register a Pod so Services can discover it."""
        self._pods[pod_name] = {"labels": labels, "ip": ip, "is_ready": is_ready}

    def deregister_pod(self, pod_name: str) -> None:
        """Remove a Pod from discovery (e.g. when it is terminated)."""
        self._pods.pop(pod_name, None)

    def resolve(self, service_name: str) -> list[Endpoint]:
        """Resolve a service name to its current endpoints.

        Returns only ready endpoints (is_ready=True).
        """
        service = self._services.get(service_name)
        if service is None:
            raise KeyError(f"Service '{service_name}' not found")

        all_pods = list(self._pods.values())
        endpoints = service.resolve(all_pods)

        # Filter to ready endpoints only
        return [ep for ep in endpoints if ep.is_ready]

    def load_balance(
        self, service_name: str, algorithm: str = "round-robin"
    ) -> Endpoint:
        """Pick one endpoint using the specified algorithm.

        Args:
            service_name: The service to load-balance.
            algorithm: "round-robin" or "random".

        Returns:
            A single Endpoint selected by the algorithm.

        Raises:
            RuntimeError: If no ready endpoints are available.
        """
        import random as _random

        endpoints = self.resolve(service_name)
        if not endpoints:
            raise RuntimeError(
                f"No ready endpoints for service '{service_name}'"
            )

        if algorithm == "random":
            return _random.choice(endpoints)

        # Round-robin
        counter = self._rr_counters.get(service_name, 0)
        endpoint = endpoints[counter % len(endpoints)]
        self._rr_counters[service_name] = counter + 1
        return endpoint
