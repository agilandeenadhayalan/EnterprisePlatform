"""
Sidecar Proxy — request interception and transparent proxying.

WHY THIS MATTERS:
In a service mesh, every Pod gets a sidecar proxy (e.g. Envoy) injected
alongside the application container. The proxy intercepts all inbound and
outbound traffic, enabling the mesh to add observability, security (mTLS),
and traffic control without changing application code.

Key concepts:
  - Sidecar injection: adds a proxy container to the Pod spec. In
    Istio, this is done by a mutating admission webhook.
  - Request interception: the proxy adds headers (x-request-id for
    tracing, x-forwarded-for for client IP) and records metrics.
  - Transparent proxying: the application talks to localhost; the
    proxy handles service discovery and load balancing.
"""

import hashlib
from uuid import uuid4


class ProxyConfig:
    """Configuration for a sidecar proxy.

    listen_port: the port the proxy listens on for inbound traffic.
    upstream_port: the port the application container listens on.
    protocol: http or grpc.
    timeout_seconds: maximum time to wait for upstream response.
    retries: number of retry attempts on failure.
    """

    def __init__(
        self,
        listen_port: int,
        upstream_port: int,
        protocol: str = "http",
        timeout_seconds: float = 30.0,
        retries: int = 3,
    ):
        self.listen_port = listen_port
        self.upstream_port = upstream_port
        self.protocol = protocol
        self.timeout_seconds = timeout_seconds
        self.retries = retries


class Request:
    """An HTTP request flowing through the proxy."""

    def __init__(self, method: str, path: str, headers: dict = None, body: str = None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.body = body


class Response:
    """An HTTP response returned by the proxy."""

    def __init__(self, status_code: int, headers: dict = None, body: str = None, latency_ms: float = 0.0):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.latency_ms = latency_ms


class SidecarProxy:
    """A sidecar proxy that intercepts and enriches HTTP requests.

    The proxy sits between the network and the application container.
    It adds observability headers, records request/error counts, and
    can enforce policies (timeouts, retries, circuit breaking).

    In Istio, this is Envoy. In Linkerd, this is linkerd2-proxy.
    Both follow the same pattern: intercept, enrich, forward, observe.
    """

    def __init__(self, config: ProxyConfig):
        self.config = config
        self._request_count: int = 0
        self._error_count: int = 0
        self._total_latency_ms: float = 0.0

    def inject(self, pod_containers: list) -> list:
        """Inject the sidecar proxy container into a Pod's container list.

        In real Kubernetes, the Istio mutating webhook does this at
        admission time. The proxy container shares the Pod's network
        namespace, so it can intercept traffic on any port.

        Args:
            pod_containers: list of container dicts with at least
                            'name' and 'image' keys.

        Returns:
            A new list with the proxy container appended.
        """
        proxy_container = {
            "name": "istio-proxy",
            "image": "envoy:latest",
            "ports": [self.config.listen_port],
        }
        return list(pod_containers) + [proxy_container]

    def handle_request(self, request: Request) -> Response:
        """Handle an inbound request through the proxy.

        The proxy:
        1. Generates a unique x-request-id for distributed tracing.
        2. Adds x-forwarded-for with the client IP (or 'unknown').
        3. Adds x-proxy-id to identify this proxy instance.
        4. Records metrics (request count, latency).

        Returns a Response with status 200 and the enriched headers.
        """
        self._request_count += 1

        # Generate a deterministic latency based on request path
        latency = 1.0 + (hash(request.path) % 5)

        request_id = uuid4().hex[:16]

        response_headers = {
            "x-request-id": request_id,
            "x-proxy-id": f"sidecar-{self.config.listen_port}",
            "x-forwarded-for": request.headers.get("x-forwarded-for", "unknown"),
        }

        self._total_latency_ms += latency

        return Response(
            status_code=200,
            headers=response_headers,
            body=request.body,
            latency_ms=latency,
        )

    def record_error(self) -> None:
        """Record an error for metrics tracking."""
        self._error_count += 1

    def get_metrics(self) -> dict:
        """Return proxy metrics for observability.

        Returns:
            A dict with request count, error count, success rate,
            and average latency in milliseconds.
        """
        success_rate = 0.0
        if self._request_count > 0:
            success_rate = (self._request_count - self._error_count) / self._request_count

        avg_latency = 0.0
        if self._request_count > 0:
            avg_latency = self._total_latency_ms / self._request_count

        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
        }
