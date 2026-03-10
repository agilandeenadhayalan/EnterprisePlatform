"""
Blast Radius Analysis — understand the impact of a service failure.

WHY THIS MATTERS:
Before injecting a failure, you need to understand its blast radius:
which other services will be affected, how deep the cascade goes, and
how many users will be impacted. This analysis prevents you from
accidentally taking down production during a chaos experiment.

A dependency graph models the service topology. When service A fails,
all services that depend on A (directly or transitively) may be affected.
The blast radius score combines the number of affected services, their
criticality, and whether they are user-facing.

Key concepts:
  - Dependency types: sync (blocking), async (non-blocking), optional
    (gracefully degraded). Sync dependencies cascade failures immediately.
  - Topological sort: process services in dependency order for safe
    deployment and rollback.
  - Impact scoring: weighted by criticality and cascade depth.
  - User impact estimation: percentage of users affected based on
    which user-facing services are in the blast radius.
"""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class ServiceNode:
    """A service in the dependency graph.

    Attributes:
        name: unique service identifier
        criticality: importance score from 1 (low) to 10 (critical)
        user_facing: True if this service directly serves user requests
    """
    name: str
    criticality: int = 5
    user_facing: bool = False


@dataclass
class Dependency:
    """A directed dependency between two services.

    Attributes:
        source: the service that depends on target
        target: the service being depended upon
        dependency_type: "sync", "async", or "optional"
    """
    source: str
    target: str
    dependency_type: str = "sync"


class DependencyGraph:
    """Directed graph of service dependencies.

    Edges go from dependent -> dependency (source -> target means
    "source depends on target"). When target fails, source is affected.
    """

    def __init__(self):
        self._services: dict[str, ServiceNode] = {}
        self._dependencies: list[Dependency] = []
        # Adjacency: service -> list of services it depends on
        self._depends_on: dict[str, list[str]] = {}
        # Reverse adjacency: service -> list of services that depend on it
        self._depended_by: dict[str, list[str]] = {}

    def add_service(self, node: ServiceNode) -> None:
        """Register a service in the graph."""
        self._services[node.name] = node
        if node.name not in self._depends_on:
            self._depends_on[node.name] = []
        if node.name not in self._depended_by:
            self._depended_by[node.name] = []

    def add_dependency(self, dep: Dependency) -> None:
        """Add a dependency edge: source depends on target."""
        self._dependencies.append(dep)
        if dep.source not in self._depends_on:
            self._depends_on[dep.source] = []
        if dep.target not in self._depended_by:
            self._depended_by[dep.target] = []

        self._depends_on[dep.source].append(dep.target)
        self._depended_by[dep.target].append(dep.source)

    def get_downstream(self, service: str) -> list[str]:
        """All services affected if this one fails (BFS through reverse edges).

        Returns services that depend on the failed service, transitively.
        """
        visited = set()
        queue = deque([service])

        while queue:
            current = queue.popleft()
            for dependent in self._depended_by.get(current, []):
                if dependent not in visited:
                    visited.add(dependent)
                    queue.append(dependent)

        return sorted(visited)

    def get_upstream(self, service: str) -> list[str]:
        """All services that this service depends on (direct dependencies)."""
        return sorted(self._depends_on.get(service, []))

    def topological_sort(self) -> list[str]:
        """Return services in dependency order (dependencies first).

        Uses Kahn's algorithm. Services with no dependencies come first.
        """
        in_degree: dict[str, int] = {s: 0 for s in self._services}
        for dep in self._dependencies:
            if dep.source in in_degree:
                in_degree[dep.source] = in_degree.get(dep.source, 0) + 1

        queue = deque(
            sorted(s for s, d in in_degree.items() if d == 0)
        )
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in self._depended_by.get(node, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        return result

    def get_service(self, name: str) -> ServiceNode | None:
        """Get a service node by name."""
        return self._services.get(name)


@dataclass
class ImpactReport:
    """Report on the blast radius of a service failure.

    Attributes:
        target: the service that failed
        affected_services: services in the blast radius
        cascade_depth: maximum depth of the failure cascade
        impact_score: weighted impact score
        user_impact_percent: estimated percentage of users affected
    """
    target: str
    affected_services: list[str]
    cascade_depth: int
    impact_score: float
    user_impact_percent: float


class BlastRadiusAnalyzer:
    """Analyze the blast radius of a service failure.

    Combines the dependency graph with service metadata (criticality,
    user-facing) to produce impact scores and user impact estimates.
    """

    def __init__(self, graph: DependencyGraph):
        self._graph = graph

    def analyze(self, target_service: str) -> ImpactReport:
        """Compute the full blast radius for a service failure."""
        affected = self._graph.get_downstream(target_service)
        cascade_depth = self._compute_cascade_depth(target_service)
        impact_score = self.get_impact_score(target_service)
        user_impact = self.get_affected_users_estimate(target_service)

        return ImpactReport(
            target=target_service,
            affected_services=affected,
            cascade_depth=cascade_depth,
            impact_score=impact_score,
            user_impact_percent=user_impact,
        )

    def _compute_cascade_depth(self, service: str) -> int:
        """Compute the maximum cascade depth from BFS levels."""
        visited = {service: 0}
        queue = deque([(service, 0)])
        max_depth = 0

        while queue:
            current, depth = queue.popleft()
            for dependent in self._graph._depended_by.get(current, []):
                if dependent not in visited:
                    new_depth = depth + 1
                    visited[dependent] = new_depth
                    max_depth = max(max_depth, new_depth)
                    queue.append((dependent, new_depth))

        return max_depth

    def get_impact_score(self, target: str) -> float:
        """Weighted impact score based on criticality and cascade depth.

        Score = sum of (criticality * (1 / depth)) for each affected service,
        plus the target's own criticality.
        """
        target_node = self._graph.get_service(target)
        base_score = target_node.criticality if target_node else 5.0

        visited = {target: 0}
        queue = deque([(target, 0)])
        total_score = base_score

        while queue:
            current, depth = queue.popleft()
            for dependent in self._graph._depended_by.get(current, []):
                if dependent not in visited:
                    new_depth = depth + 1
                    visited[dependent] = new_depth
                    node = self._graph.get_service(dependent)
                    crit = node.criticality if node else 5
                    total_score += crit / new_depth
                    queue.append((dependent, new_depth))

        return round(total_score, 2)

    def get_affected_users_estimate(self, target: str) -> float:
        """Estimate percentage of users affected by the failure.

        Counts user-facing services in the blast radius. If the target
        itself is user-facing, that counts too. Each user-facing service
        is assumed to serve an equal share of users.
        """
        all_services = list(self._graph._services.keys())
        total_user_facing = sum(
            1 for s in all_services
            if self._graph.get_service(s) and self._graph.get_service(s).user_facing
        )

        if total_user_facing == 0:
            return 0.0

        affected = self._graph.get_downstream(target)
        # Include target itself
        affected_set = set(affected) | {target}

        affected_user_facing = sum(
            1 for s in affected_set
            if self._graph.get_service(s) and self._graph.get_service(s).user_facing
        )

        return round(100.0 * affected_user_facing / total_user_facing, 1)
