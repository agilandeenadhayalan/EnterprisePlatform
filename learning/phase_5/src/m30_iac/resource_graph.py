"""
Resource Graph — DAG-based resource dependency resolution.

WHY THIS MATTERS:
Infrastructure resources have dependencies: a database security group
must exist before the database instance, which must exist before the
application server. Terraform builds a Directed Acyclic Graph (DAG) of
these dependencies and processes them in topological order.

Key concepts:
  - Topological sort: process resources in dependency order so that
    every resource is created after all its dependencies.
  - Cycle detection: circular dependencies (A depends on B, B depends
    on A) are invalid and must be detected before apply.
  - Impact analysis: when changing a resource, find all transitively
    affected resources (everything that depends on it, directly or
    indirectly).
  - Kahn's algorithm: a BFS-based topological sort that also naturally
    detects cycles (if the sorted output has fewer nodes than the graph,
    there is a cycle).
"""

from collections import deque


class Resource:
    """A single infrastructure resource (e.g. aws_instance, aws_vpc).

    Each resource has a type and name that form its unique ID
    (e.g. "aws_vpc.main"), properties describing its configuration,
    and a list of dependencies (other resource IDs it depends on).

    In Terraform HCL:
        resource "aws_instance" "web" {
          ami           = "ami-123"
          subnet_id     = aws_subnet.main.id  # depends_on
        }
    """

    def __init__(self, type: str, name: str, properties: dict = None, depends_on: list = None):
        self.type = type
        self.name = name
        self.properties = properties or {}
        self.depends_on = depends_on or []

    @property
    def resource_id(self) -> str:
        """Unique identifier in the format 'type.name'."""
        return f"{self.type}.{self.name}"

    def to_dict(self) -> dict:
        """Serialize the resource for state storage."""
        return {
            "type": self.type,
            "name": self.name,
            "resource_id": self.resource_id,
            "properties": self.properties,
            "depends_on": self.depends_on,
        }


class ResourceGraph:
    """A DAG of infrastructure resources and their dependencies.

    The graph supports:
    - Topological ordering (Kahn's algorithm) for create/update order.
    - Cycle detection to catch invalid dependency configurations.
    - Reverse dependency lookup to find what depends on a resource.
    - Transitive impact analysis to find all affected resources.

    In Terraform, this graph is built from the HCL configuration and
    used to determine the order of operations during plan and apply.
    """

    def __init__(self):
        self._resources: dict[str, Resource] = {}

    def add_resource(self, resource: Resource) -> None:
        """Add a resource to the graph."""
        self._resources[resource.resource_id] = resource

    def remove_resource(self, resource_id: str) -> None:
        """Remove a resource from the graph.

        Also removes this resource from other resources' depends_on lists.
        """
        if resource_id in self._resources:
            del self._resources[resource_id]
            # Clean up references
            for r in self._resources.values():
                if resource_id in r.depends_on:
                    r.depends_on.remove(resource_id)

    def get_resource(self, resource_id: str) -> Resource:
        """Get a resource by its ID.

        Raises:
            KeyError: if the resource is not found.
        """
        if resource_id not in self._resources:
            raise KeyError(f"Resource '{resource_id}' not found")
        return self._resources[resource_id]

    def get_dependency_order(self) -> list:
        """Return resource IDs in topological order using Kahn's algorithm.

        Resources with no dependencies come first, followed by resources
        whose dependencies have already been listed. This is the order
        in which resources should be created.

        Raises:
            ValueError: if the graph contains cycles.
        """
        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {rid: 0 for rid in self._resources}
        adjacency: dict[str, list[str]] = {rid: [] for rid in self._resources}

        for rid, resource in self._resources.items():
            for dep in resource.depends_on:
                if dep in self._resources:
                    adjacency[dep].append(rid)
                    in_degree[rid] += 1

        # Start with nodes that have no dependencies
        queue = deque([rid for rid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._resources):
            raise ValueError("Dependency graph contains cycles")

        return result

    def detect_cycles(self) -> list:
        """Detect cycles in the dependency graph using DFS.

        Returns:
            A list of cycles, where each cycle is a list of resource_ids
            forming the cycle. Returns an empty list if no cycles exist.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {rid: WHITE for rid in self._resources}
        path = []
        cycles = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)

            resource = self._resources[node]
            for dep in resource.depends_on:
                if dep not in self._resources:
                    continue
                if color[dep] == GRAY:
                    # Found a cycle — extract it from the path
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    cycles.append(cycle)
                elif color[dep] == WHITE:
                    dfs(dep)

            path.pop()
            color[node] = BLACK

        for rid in self._resources:
            if color[rid] == WHITE:
                dfs(rid)

        return cycles

    def get_dependents(self, resource_id: str) -> list:
        """Find all resources that directly depend on the given resource.

        This is the reverse lookup: "what breaks if I change this?"
        """
        dependents = []
        for rid, resource in self._resources.items():
            if resource_id in resource.depends_on:
                dependents.append(resource)
        return dependents

    def get_affected(self, resource_id: str) -> list:
        """Find all transitively affected resources using BFS.

        If resource A depends on B, and B depends on C, then changing C
        affects both B and A. This is used by Terraform to determine
        which resources need to be re-planned after a change.

        Returns:
            A list of resource_ids that are transitively affected.
        """
        affected = []
        visited = set()
        queue = deque([resource_id])
        visited.add(resource_id)

        while queue:
            current = queue.popleft()
            dependents = self.get_dependents(current)
            for dep in dependents:
                if dep.resource_id not in visited:
                    visited.add(dep.resource_id)
                    affected.append(dep.resource_id)
                    queue.append(dep.resource_id)

        return affected
