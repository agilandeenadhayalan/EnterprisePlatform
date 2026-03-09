"""
Traffic Routing — weighted routing, header-based routing, and canary deploys.

WHY THIS MATTERS:
Service meshes give you fine-grained control over where traffic goes.
This enables:
  - Canary deployments: send 5% of traffic to v2, 95% to v1.
  - A/B testing: route users with a specific header to a test backend.
  - Blue/green deployments: instantly shift 100% traffic between versions.

Key concepts:
  - Weight-based routing: each destination gets a percentage of traffic.
    Weights must sum to 100. Routing is deterministic: the same
    request_id always goes to the same destination (via hashing).
  - Header-based routing: match specific headers to route to a
    destination. First matching rule wins.
  - Traffic splitting: combine both for sophisticated rollout strategies.
"""


class TrafficRule:
    """A single traffic routing rule.

    Each rule maps to a destination service with a weight (0-100)
    and optional header matchers. In Istio, this is a VirtualService
    HTTPRouteDestination.

    weight: percentage of traffic for this destination (0-100).
    match_headers: optional dict of header key-value pairs that must
                   ALL be present in the request for this rule to match.
    """

    def __init__(self, destination: str, weight: int = 100, match_headers: dict = None):
        self.destination = destination
        self.weight = weight
        self.match_headers = match_headers or {}


class WeightedRouter:
    """Routes traffic to destinations based on percentage weights.

    Routing is deterministic: hash(request_id) % 100 maps to a weight
    range. This ensures that the same request_id always reaches the
    same destination, which is important for session affinity and
    debugging.

    Example: rules = [("v1", 90), ("v2", 10)]
    - request_ids hashing to 0-89  go to v1
    - request_ids hashing to 90-99 go to v2
    """

    def __init__(self):
        self.rules: list[TrafficRule] = []

    def add_rule(self, rule: TrafficRule) -> None:
        """Add a traffic rule."""
        self.rules.append(rule)

    def validate(self) -> bool:
        """Validate that weights sum to exactly 100.

        In Istio, VirtualService validation rejects configurations
        where weights don't sum to 100. This prevents traffic from
        being silently dropped or over-allocated.
        """
        total = sum(rule.weight for rule in self.rules)
        return total == 100

    def route(self, request_id: str) -> str:
        """Route a request to a destination based on its hash.

        Uses a deterministic hash of the request_id to select a
        destination from the weighted ranges. This ensures consistent
        routing for the same request_id across retries.

        Args:
            request_id: a unique identifier for the request.

        Returns:
            The destination service name.
        """
        # Deterministic hash: same request_id always gets same bucket
        bucket = hash(request_id) % 100
        cumulative = 0
        for rule in self.rules:
            cumulative += rule.weight
            if bucket < cumulative:
                return rule.destination
        # Fallback to last rule (shouldn't happen if weights sum to 100)
        return self.rules[-1].destination

    def get_traffic_distribution(self, n_requests: int) -> dict:
        """Simulate traffic distribution over n_requests.

        Returns a dict of destination -> count showing how traffic
        would be distributed. Useful for verifying that weights are
        working as expected.
        """
        distribution: dict[str, int] = {}
        for i in range(n_requests):
            dest = self.route(f"request-{i}")
            distribution[dest] = distribution.get(dest, 0) + 1
        return distribution


class HeaderBasedRouter:
    """Routes traffic based on request header matching.

    Header-based routing is used for:
    - Canary testing: route internal users (x-canary: true) to v2.
    - Feature flags: route users with specific features to test backends.
    - Multi-tenancy: route by tenant ID header.

    Rules are evaluated in order. The first rule whose match_headers
    are ALL present in the request wins. If no rule matches, the
    default destination is returned.
    """

    def __init__(self, rules: list = None, default_destination: str = "default"):
        self.rules: list[TrafficRule] = rules or []
        self.default_destination = default_destination

    def route(self, headers: dict) -> str:
        """Route a request based on its headers.

        Each rule's match_headers must ALL be present in the request
        headers with matching values. First match wins.

        Args:
            headers: the request headers as a dict.

        Returns:
            The destination service name, or default_destination if
            no rule matches.
        """
        for rule in self.rules:
            if not rule.match_headers:
                continue
            all_match = True
            for key, value in rule.match_headers.items():
                if headers.get(key) != value:
                    all_match = False
                    break
            if all_match:
                return rule.destination

        return self.default_destination
