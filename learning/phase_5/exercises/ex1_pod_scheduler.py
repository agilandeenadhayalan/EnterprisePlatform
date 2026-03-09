"""
Exercise 1: Pod Scheduler — Resource-Aware Scheduling
========================================
Implement a pod scheduler that assigns pods to nodes based on available resources.
The scheduler should find the best-fitting node (least waste) that has enough
CPU and memory for the pod.

WHY THIS MATTERS:
The Kubernetes scheduler's job is to find the best node for each Pod. A naive
approach (first-fit) leads to resource fragmentation: some nodes overloaded,
others nearly empty. The best-fit strategy minimizes waste by placing Pods
on nodes where they fit most tightly, improving cluster utilization.

Key concepts:
- Bin packing: minimize resource fragmentation by filling nodes tightly
- Resource requests vs limits: scheduling is based on requests (guaranteed)
- Node capacity tracking: track used vs available resources
- Scoring: rank nodes by how well a pod fits (lower waste = better)

YOUR TASK:
1. Implement can_fit(node, pod) — check if a node has enough resources
2. Implement score_node(node, pod) — score how tightly a pod fits a node
3. Implement schedule(pod, nodes) — find the best node and reserve resources
"""


class Node:
    """A Kubernetes worker node with finite resources.

    Each node has a total capacity and tracks how much is currently used.
    The available resources are total minus used.
    """

    def __init__(self, name: str, cpu_millicores: int, memory_mb: int):
        self.name = name
        self.total_cpu = cpu_millicores
        self.total_memory = memory_mb
        self.used_cpu = 0
        self.used_memory = 0

    @property
    def available_cpu(self) -> int:
        return self.total_cpu - self.used_cpu

    @property
    def available_memory(self) -> int:
        return self.total_memory - self.used_memory


class PodRequest:
    """A pod requesting specific resources."""

    def __init__(self, name: str, cpu_millicores: int, memory_mb: int):
        self.name = name
        self.cpu = cpu_millicores
        self.memory = memory_mb


class PodScheduler:
    """
    Schedules pods to nodes using a best-fit decreasing strategy.

    TODO: Implement these methods:

    1. can_fit(node, pod) -> bool
       Check if a node has enough available CPU AND memory for the pod.

    2. score_node(node, pod) -> float
       Score how well a pod fits a node. Lower waste = better score.
       Score = (remaining_cpu_after / total_cpu + remaining_memory_after / total_memory) / 2
       This prefers nodes where the pod fits tightly (less waste).
       Return float('inf') if pod doesn't fit.

    3. schedule(pod, nodes) -> str or None
       Find the best node for a pod. Returns node name or None if no fit.
       Pick the node with the LOWEST score (tightest fit).
       Update the chosen node's used_cpu and used_memory.
    """

    def can_fit(self, node: Node, pod: PodRequest) -> bool:
        # YOUR CODE HERE (2 lines)
        raise NotImplementedError("Implement can_fit")

    def score_node(self, node: Node, pod: PodRequest) -> float:
        # YOUR CODE HERE (5 lines)
        raise NotImplementedError("Implement score_node")

    def schedule(self, pod: PodRequest, nodes: list) -> str | None:
        # YOUR CODE HERE (8 lines)
        raise NotImplementedError("Implement schedule")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    scheduler = PodScheduler()

    # Test 1: can_fit
    node = Node("n1", cpu_millicores=1000, memory_mb=2048)
    pod = PodRequest("p1", cpu_millicores=500, memory_mb=1024)
    assert scheduler.can_fit(node, pod), "Pod should fit on node"
    print("[PASS] can_fit: pod fits on node")

    big_pod = PodRequest("p2", cpu_millicores=2000, memory_mb=1024)
    assert not scheduler.can_fit(node, big_pod), "Pod should NOT fit on node"
    print("[PASS] can_fit: oversized pod rejected")

    # Test 2: score_node
    small_node = Node("small", cpu_millicores=1000, memory_mb=1024)
    big_node = Node("big", cpu_millicores=4000, memory_mb=8192)
    pod = PodRequest("p1", cpu_millicores=800, memory_mb=900)
    small_score = scheduler.score_node(small_node, pod)
    big_score = scheduler.score_node(big_node, pod)
    assert small_score < big_score, (
        f"Small node should score better (lower). "
        f"Small={small_score:.3f}, Big={big_score:.3f}"
    )
    print(f"[PASS] score_node: small={small_score:.3f} < big={big_score:.3f}")

    # Test 3: schedule picks best-fit
    nodes = [
        Node("large", cpu_millicores=4000, memory_mb=8192),
        Node("medium", cpu_millicores=2000, memory_mb=4096),
        Node("small", cpu_millicores=1000, memory_mb=2048),
    ]
    pod = PodRequest("web", cpu_millicores=800, memory_mb=1500)
    result = scheduler.schedule(pod, nodes)
    assert result == "small", f"Expected 'small', got '{result}'"
    print(f"[PASS] schedule: picked '{result}' (tightest fit)")

    # Test 4: schedule returns None if no fit
    tiny_pod = PodRequest("big", cpu_millicores=10000, memory_mb=32768)
    result = scheduler.schedule(tiny_pod, nodes)
    assert result is None, f"Expected None, got '{result}'"
    print("[PASS] schedule: returns None when no node fits")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
