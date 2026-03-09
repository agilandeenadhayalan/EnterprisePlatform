"""
Exercise 6: Terraform Planner — Resource Dependency Resolution
========================================
Implement a resource planner that resolves dependencies between infrastructure
resources using topological sort (Kahn's algorithm) and detects circular
dependencies.

WHY THIS MATTERS:
When Terraform creates infrastructure, it must respect dependencies:
  - A subnet needs its VPC to exist first.
  - An EC2 instance needs its subnet and security group first.
  - A database needs its subnet group and parameter group first.

If Terraform tried to create them in random order, most would fail because
their dependencies don't exist yet. Topological sort ensures every resource
is created after all its dependencies.

Key concepts:
- Directed Acyclic Graph (DAG): resources are nodes, dependencies are edges
- In-degree: the number of dependencies a resource has
- Kahn's algorithm: BFS starting from nodes with in-degree 0 (no dependencies)
- Cycle detection: if not all nodes are processed, there's a cycle

YOUR TASK:
1. Implement plan(resources) using Kahn's algorithm
2. Return resources in dependency order (dependencies first)
3. Raise ValueError if circular dependencies are detected
"""

from collections import deque


class InfraResource:
    """An infrastructure resource with dependencies.

    name: unique identifier (e.g. "vpc", "subnet", "instance")
    depends_on: list of resource names this resource depends on
    """

    def __init__(self, name: str, depends_on: list = None):
        self.name = name
        self.depends_on = depends_on or []


class ResourcePlanner:
    """
    Plans resource creation order using topological sort.

    TODO: Implement the plan method:

    plan(resources: list[InfraResource]) -> list[str]

    Algorithm (Kahn's Algorithm):
    1. Build an in-degree map: for each resource, count how many
       dependencies it has (only counting dependencies that are in
       the resource list).
    2. Build an adjacency list: for each resource, list which
       resources depend on it.
    3. Start with a queue of all resources with in-degree 0
       (no dependencies — they can be created first).
    4. While the queue is not empty:
       a. Pop a resource from the queue.
       b. Add it to the result list.
       c. For each resource that depends on it, decrement its in-degree.
       d. If the in-degree reaches 0, add it to the queue.
    5. If the result list has fewer items than the input, there's a
       cycle — raise ValueError.

    Returns:
        A list of resource names in creation order (dependencies first).

    Raises:
        ValueError: if circular dependencies are detected.
    """

    def plan(self, resources: list) -> list:
        # YOUR CODE HERE (~20 lines)
        raise NotImplementedError("Implement plan")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    planner = ResourcePlanner()

    # Test 1: Simple linear chain
    resources = [
        InfraResource("instance", depends_on=["subnet"]),
        InfraResource("subnet", depends_on=["vpc"]),
        InfraResource("vpc"),
    ]
    order = planner.plan(resources)
    assert order.index("vpc") < order.index("subnet"), "VPC must come before subnet"
    assert order.index("subnet") < order.index("instance"), "Subnet must come before instance"
    print(f"[PASS] Linear chain: {order}")

    # Test 2: Parallel resources
    resources = [
        InfraResource("web", depends_on=["vpc"]),
        InfraResource("db", depends_on=["vpc"]),
        InfraResource("vpc"),
    ]
    order = planner.plan(resources)
    assert order[0] == "vpc", f"VPC should be first, got {order[0]}"
    assert set(order[1:]) == {"web", "db"}, "Web and DB should come after VPC"
    print(f"[PASS] Parallel resources: {order}")

    # Test 3: No dependencies
    resources = [
        InfraResource("a"),
        InfraResource("b"),
        InfraResource("c"),
    ]
    order = planner.plan(resources)
    assert len(order) == 3, f"Expected 3 resources, got {len(order)}"
    print(f"[PASS] No dependencies: {order}")

    # Test 4: Cycle detection
    resources = [
        InfraResource("a", depends_on=["b"]),
        InfraResource("b", depends_on=["c"]),
        InfraResource("c", depends_on=["a"]),
    ]
    try:
        planner.plan(resources)
        assert False, "Should have raised ValueError for cycle"
    except ValueError:
        print("[PASS] Circular dependency detected and raised ValueError")

    # Test 5: Complex DAG
    resources = [
        InfraResource("app", depends_on=["subnet", "sg"]),
        InfraResource("subnet", depends_on=["vpc"]),
        InfraResource("sg", depends_on=["vpc"]),
        InfraResource("vpc"),
        InfraResource("dns", depends_on=["app"]),
    ]
    order = planner.plan(resources)
    assert order.index("vpc") < order.index("subnet"), "VPC before subnet"
    assert order.index("vpc") < order.index("sg"), "VPC before security group"
    assert order.index("subnet") < order.index("app"), "Subnet before app"
    assert order.index("sg") < order.index("app"), "SG before app"
    assert order.index("app") < order.index("dns"), "App before DNS"
    print(f"[PASS] Complex DAG: {order}")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
