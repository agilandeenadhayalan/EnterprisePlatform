"""
Pod Specification & Lifecycle — the atomic unit of Kubernetes scheduling.

WHY THIS MATTERS:
A Pod is the smallest deployable unit in Kubernetes. It wraps one or more
containers that share networking and storage. Understanding how Pods are
specified, validated, and transitioned through lifecycle states is
foundational to everything else in Kubernetes.

Key concepts:
  - Resource Requests vs Limits: Requests are *guaranteed* resources used
    for scheduling decisions. Limits are the *maximum* a container may use.
    Limits must always be >= requests.
  - Pod Validation: Kubernetes rejects Pods with duplicate container names,
    port conflicts, or empty container lists at admission time.
  - Lifecycle State Machine: PENDING -> RUNNING -> SUCCEEDED / FAILED.
    Invalid transitions (e.g. PENDING -> SUCCEEDED) are rejected.
"""

from enum import Enum


class PodStatus(Enum):
    """Lifecycle states for a Kubernetes Pod.

    PENDING   — Pod accepted but not yet running (waiting for scheduling).
    RUNNING   — At least one container is running.
    SUCCEEDED — All containers terminated successfully (exit code 0).
    FAILED    — At least one container terminated with a non-zero exit code.
    UNKNOWN   — State cannot be determined (e.g. node communication lost).
    """

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class ResourceRequirements:
    """CPU and memory resource specification for a container.

    In real Kubernetes, CPU is measured in millicores (1000m = 1 CPU core)
    and memory in bytes, but we use MB for simplicity.

    Resource requests tell the scheduler how much capacity to reserve.
    Resource limits tell the kubelet when to throttle or OOM-kill.
    """

    def __init__(self, cpu_millicores: int, memory_mb: int):
        if cpu_millicores < 0 or memory_mb < 0:
            raise ValueError("Resource values must be non-negative")
        self.cpu_millicores = cpu_millicores
        self.memory_mb = memory_mb

    def fits_within(self, limits: "ResourceRequirements") -> bool:
        """Check whether these requirements fit within the given limits.

        This is used to verify that resource requests do not exceed limits.
        """
        return (
            self.cpu_millicores <= limits.cpu_millicores
            and self.memory_mb <= limits.memory_mb
        )

    def __repr__(self) -> str:
        return f"ResourceRequirements(cpu={self.cpu_millicores}m, mem={self.memory_mb}Mi)"


class Container:
    """A single container within a Pod.

    Mirrors the Kubernetes Container spec: each container has an image,
    exposed ports, environment variables, and resource constraints.

    Validation rule: resource_limits must be >= resource_requests for each
    dimension. This ensures the scheduler can guarantee the requested
    resources while the container has headroom up to the limit.
    """

    def __init__(
        self,
        name: str,
        image: str,
        ports: list[int] | None = None,
        env: dict[str, str] | None = None,
        resource_requests: ResourceRequirements | None = None,
        resource_limits: ResourceRequirements | None = None,
    ):
        if not name:
            raise ValueError("Container name must be non-empty")

        self.name = name
        self.image = image
        self.ports = ports or []
        self.env = env or {}
        self.resource_requests = resource_requests
        self.resource_limits = resource_limits

        # Validate that limits >= requests when both are set
        if self.resource_requests and self.resource_limits:
            if not self.resource_requests.fits_within(self.resource_limits):
                raise ValueError(
                    f"Container '{name}': resource_limits must be >= resource_requests. "
                    f"Requests={self.resource_requests}, Limits={self.resource_limits}"
                )

    def __repr__(self) -> str:
        return f"Container(name='{self.name}', image='{self.image}')"


class PodSpec:
    """Full Pod specification — the declarative definition of a Pod.

    A PodSpec groups one or more containers that are co-located, share
    the same network namespace (localhost), and are scheduled as a unit.

    Validation rules enforced at creation:
      1. Must have at least one container.
      2. Container names must be unique within the Pod.
      3. No two containers may expose the same port.

    These mirror the real Kubernetes admission checks.
    """

    def __init__(
        self,
        name: str,
        namespace: str = "default",
        containers: list[Container] | None = None,
        restart_policy: str = "Always",
        node_selector: dict[str, str] | None = None,
    ):
        self.name = name
        self.namespace = namespace
        self.containers = containers or []
        self.restart_policy = restart_policy
        self.node_selector = node_selector or {}
        self.labels: dict[str, str] = {}

        self._validate()

    def _validate(self) -> None:
        """Validate the PodSpec against Kubernetes admission rules."""
        if not self.containers:
            raise ValueError(f"Pod '{self.name}': must have at least one container")

        # Check for duplicate container names
        names = [c.name for c in self.containers]
        if len(names) != len(set(names)):
            dupes = [n for n in names if names.count(n) > 1]
            raise ValueError(
                f"Pod '{self.name}': duplicate container names: {set(dupes)}"
            )

        # Check for port conflicts across containers
        all_ports: list[int] = []
        for container in self.containers:
            for port in container.ports:
                if port in all_ports:
                    raise ValueError(
                        f"Pod '{self.name}': port {port} is exposed by multiple containers"
                    )
                all_ports.append(port)

    def __repr__(self) -> str:
        return (
            f"PodSpec(name='{self.name}', ns='{self.namespace}', "
            f"containers={len(self.containers)})"
        )


class PodLifecycle:
    """State machine for Pod lifecycle transitions.

    Models the valid transitions in a Kubernetes Pod's lifecycle:

        PENDING ──schedule()──> PENDING  (marks pod as scheduled, stays pending)
        PENDING ──start()────> RUNNING
        RUNNING ──succeed()──> SUCCEEDED
        RUNNING ──fail()─────> FAILED

    Any transition not listed above raises ValueError. This prevents
    impossible states like jumping from PENDING directly to SUCCEEDED.

    WHY A STATE MACHINE:
    Kubernetes controllers are reconciliation loops that compare *desired*
    state to *actual* state. The lifecycle state machine defines what
    actual states are reachable, preventing controllers from making
    nonsensical transitions.
    """

    def __init__(self, pod_name: str):
        self.pod_name = pod_name
        self.status = PodStatus.PENDING
        self.scheduled = False

    def schedule(self) -> None:
        """Mark the Pod as scheduled to a node.

        In real Kubernetes, the scheduler assigns the Pod to a node.
        The Pod remains PENDING until the kubelet starts it.
        """
        if self.status != PodStatus.PENDING:
            raise ValueError(
                f"Pod '{self.pod_name}': cannot schedule from {self.status.value}"
            )
        self.scheduled = True

    def start(self) -> None:
        """Transition PENDING -> RUNNING.

        The kubelet has pulled the image and started containers.
        """
        if self.status != PodStatus.PENDING:
            raise ValueError(
                f"Pod '{self.pod_name}': cannot start from {self.status.value}, "
                f"must be PENDING"
            )
        self.status = PodStatus.RUNNING

    def succeed(self) -> None:
        """Transition RUNNING -> SUCCEEDED.

        All containers exited with code 0.
        """
        if self.status != PodStatus.RUNNING:
            raise ValueError(
                f"Pod '{self.pod_name}': cannot succeed from {self.status.value}, "
                f"must be RUNNING"
            )
        self.status = PodStatus.SUCCEEDED

    def fail(self) -> None:
        """Transition RUNNING -> FAILED.

        At least one container exited with a non-zero code.
        """
        if self.status != PodStatus.RUNNING:
            raise ValueError(
                f"Pod '{self.pod_name}': cannot fail from {self.status.value}, "
                f"must be RUNNING"
            )
        self.status = PodStatus.FAILED

    def __repr__(self) -> str:
        return f"PodLifecycle(pod='{self.pod_name}', status={self.status.value})"
