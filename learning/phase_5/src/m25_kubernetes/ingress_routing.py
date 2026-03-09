"""
Ingress Routing — HTTP path-based routing into the cluster.

WHY THIS MATTERS:
While Services handle internal routing, Ingress is the standard way to
expose HTTP/HTTPS routes from outside the cluster. An Ingress resource
defines rules that map external hostnames and URL paths to internal
Services.

Key concepts:
  - Host-based routing: requests to "api.example.com" go to one Service,
    "web.example.com" to another.
  - Path-based routing: "/api/v1" goes to the API service, "/static" to
    the CDN service, all on the same host.
  - Path matching precedence:
    1. Exact matches have highest priority (path_type="Exact")
    2. Among Prefix matches, the longest prefix wins
  - TLS termination: Ingress can terminate TLS using a referenced Secret
    containing the certificate and key.

In real Kubernetes, an Ingress Controller (nginx, traefik, envoy)
watches Ingress resources and configures the reverse proxy accordingly.
"""


class IngressPath:
    """A single path rule mapping a URL path to a backend Service.

    Attributes:
        path: The URL path to match (e.g. "/api" or "/api/v1/users").
        path_type: "Exact" for exact match, "Prefix" for prefix match.
        backend_service: Name of the Kubernetes Service to route to.
        backend_port: Port on the Service to forward traffic to.
    """

    def __init__(
        self,
        path: str,
        path_type: str,
        backend_service: str,
        backend_port: int,
    ):
        if path_type not in ("Exact", "Prefix"):
            raise ValueError(f"path_type must be 'Exact' or 'Prefix', got '{path_type}'")
        self.path = path
        self.path_type = path_type
        self.backend_service = backend_service
        self.backend_port = backend_port

    def matches(self, request_path: str) -> bool:
        """Check if a request path matches this rule."""
        if self.path_type == "Exact":
            return request_path == self.path
        # Prefix match
        return request_path == self.path or request_path.startswith(self.path.rstrip("/") + "/")

    def __repr__(self) -> str:
        return (
            f"IngressPath({self.path_type}:'{self.path}' -> "
            f"{self.backend_service}:{self.backend_port})"
        )


class IngressRule:
    """A host-level routing rule containing one or more path rules.

    Attributes:
        host: The hostname to match (e.g. "api.example.com").
        paths: List of IngressPath rules for this host.
        tls_secret: Optional name of the TLS Secret for HTTPS termination.
    """

    def __init__(
        self,
        host: str,
        paths: list[IngressPath],
        tls_secret: str | None = None,
    ):
        self.host = host
        self.paths = paths
        self.tls_secret = tls_secret

    def __repr__(self) -> str:
        tls = " (TLS)" if self.tls_secret else ""
        return f"IngressRule(host='{self.host}', paths={len(self.paths)}{tls})"


class IngressController:
    """Routes incoming HTTP requests to backend Services based on Ingress rules.

    The controller evaluates rules in this priority order:
      1. Match the request host against rule hosts.
      2. Among matching paths:
         a. Exact matches take priority over Prefix matches.
         b. Among Prefix matches, the longest matching prefix wins.

    This mirrors how nginx-ingress and traefik evaluate Ingress resources.

    WHY PATH PRIORITY MATTERS:
    Without clear priority rules, overlapping paths like "/api" and
    "/api/v1" would be ambiguous. The longest-prefix-wins rule ensures
    more specific routes take precedence, which is the intuitive behavior.
    """

    def __init__(self):
        self._rules: list[IngressRule] = []

    def add_rule(self, rule: IngressRule) -> None:
        """Add an Ingress rule to the controller."""
        self._rules.append(rule)

    def route_request(self, host: str, path: str) -> tuple[str, int] | None:
        """Route an incoming request to a backend (service, port).

        Matching algorithm:
          1. Find rules matching the host.
          2. Collect all paths that match the request path.
          3. Prefer Exact matches over Prefix matches.
          4. Among Prefix matches, pick the longest prefix.

        Returns:
            (backend_service, backend_port) or None if no match.
        """
        # Find all matching paths across rules for this host
        exact_matches: list[IngressPath] = []
        prefix_matches: list[IngressPath] = []

        for rule in self._rules:
            if rule.host != host:
                continue
            for ingress_path in rule.paths:
                if ingress_path.matches(path):
                    if ingress_path.path_type == "Exact":
                        exact_matches.append(ingress_path)
                    else:
                        prefix_matches.append(ingress_path)

        # Exact matches take priority
        if exact_matches:
            winner = exact_matches[0]
            return winner.backend_service, winner.backend_port

        # Among prefix matches, longest prefix wins
        if prefix_matches:
            prefix_matches.sort(key=lambda p: len(p.path), reverse=True)
            winner = prefix_matches[0]
            return winner.backend_service, winner.backend_port

        return None

    def is_tls(self, host: str) -> bool:
        """Check if a host has TLS configured."""
        for rule in self._rules:
            if rule.host == host and rule.tls_secret is not None:
                return True
        return False

    def get_backends(self) -> set[tuple[str, int]]:
        """Return all unique (service, port) backends across all rules."""
        backends: set[tuple[str, int]] = set()
        for rule in self._rules:
            for ingress_path in rule.paths:
                backends.add((ingress_path.backend_service, ingress_path.backend_port))
        return backends
