"""
Deployment Controller — ReplicaSet management and rolling updates.

WHY THIS MATTERS:
In Kubernetes, you rarely create Pods directly. Instead, a Deployment
controller manages ReplicaSets which in turn manage Pods. The Deployment
controller implements *reconciliation*: continuously adjusting the actual
state to match the desired state.

Key concepts:
  - ReplicaSet: maintains a stable set of identical Pods.
  - Rolling Update: gradually replaces old Pods with new ones, respecting
    max_surge (how many extra Pods above desired) and max_unavailable
    (how many Pods can be down during the update).
  - Revision History: each update creates a new ReplicaSet revision,
    enabling instant rollback to any prior version.

The reconcile loop is the heart of Kubernetes' self-healing: if a Pod
dies, the controller notices current < desired and creates a replacement.
"""

from .pod_spec import PodSpec


class ReplicaSet:
    """A set of identical Pod replicas managed by a Deployment.

    In real Kubernetes, the ReplicaSet controller watches for Pods with
    matching labels and creates/deletes Pods to match desired_replicas.

    Attributes:
        name: ReplicaSet name (usually deployment-name + revision hash).
        desired_replicas: How many Pods should exist.
        current_replicas: How many Pods actually exist right now.
        pod_template: The PodSpec template used to create new Pods.
        revision: Monotonically increasing revision number.
    """

    def __init__(
        self,
        name: str,
        desired_replicas: int,
        pod_template: PodSpec,
        revision: int,
    ):
        self.name = name
        self.desired_replicas = desired_replicas
        self.current_replicas = 0
        self.pod_template = pod_template
        self.revision = revision

    def __repr__(self) -> str:
        return (
            f"ReplicaSet(name='{self.name}', desired={self.desired_replicas}, "
            f"current={self.current_replicas}, rev={self.revision})"
        )


class DeploymentController:
    """Manages ReplicaSets to achieve desired Pod count and rolling updates.

    This models the Kubernetes Deployment controller's core logic:

    SCALE:
      Adjusts the desired replica count. The reconcile loop then drives
      actual toward desired.

    RECONCILE:
      Each call to reconcile() adjusts current_replicas by at most
      max_surge (scale up) or max_unavailable (scale down) toward the
      desired count. In real Kubernetes, this runs continuously.

    ROLLING UPDATE:
      When the Pod template changes, a new ReplicaSet is created and the
      old one is scaled down while the new one is scaled up, subject to
      surge/unavailable constraints.

    ROLLBACK:
      Reverts to a previous ReplicaSet revision, restoring the old Pod
      template and creating a new revision entry.

    Strategies:
      - RollingUpdate: gradual replacement (default, zero-downtime).
      - Recreate: kill all old Pods first, then create new ones.
    """

    def __init__(
        self,
        name: str,
        replicas: int,
        pod_template: PodSpec,
        strategy: str = "RollingUpdate",
        max_surge: int = 1,
        max_unavailable: int = 0,
    ):
        self.name = name
        self.replicas = replicas
        self.pod_template = pod_template
        self.strategy = strategy
        self.max_surge = max_surge
        self.max_unavailable = max_unavailable

        # Create initial ReplicaSet at revision 1
        initial_rs = ReplicaSet(
            name=f"{name}-rev1",
            desired_replicas=replicas,
            pod_template=pod_template,
            revision=1,
        )
        initial_rs.current_replicas = replicas

        self._revisions: list[ReplicaSet] = [initial_rs]
        self._current_revision = 1

    @property
    def active_replica_set(self) -> ReplicaSet:
        """The currently active ReplicaSet."""
        return self._revisions[-1]

    def scale(self, desired: int) -> ReplicaSet:
        """Set the desired replica count.

        Updates the active ReplicaSet's desired_replicas. The actual
        scaling happens during reconcile() calls.
        """
        if desired < 0:
            raise ValueError("Desired replicas must be non-negative")
        self.replicas = desired
        self.active_replica_set.desired_replicas = desired
        return self.active_replica_set

    def reconcile(self) -> tuple[int, int]:
        """Run one reconciliation step.

        Moves current_replicas toward desired_replicas, constrained by
        max_surge (for scale-up) and max_unavailable (for scale-down).

        Returns:
            (current_replicas, desired_replicas) after this step.
        """
        rs = self.active_replica_set
        current = rs.current_replicas
        desired = rs.desired_replicas

        if current < desired:
            # Scale up: add at most max_surge pods
            increment = min(self.max_surge, desired - current)
            rs.current_replicas += increment
        elif current > desired:
            # Scale down: remove at most max(max_unavailable, 1) pods
            max_down = max(self.max_unavailable, 1)
            decrement = min(max_down, current - desired)
            rs.current_replicas -= decrement

        return rs.current_replicas, rs.desired_replicas

    def update(self, new_template: PodSpec) -> ReplicaSet:
        """Trigger a rolling update with a new Pod template.

        Creates a new ReplicaSet revision. The old ReplicaSet's desired
        is set to 0 and the new one takes over.

        In Recreate strategy, old pods are killed immediately.
        In RollingUpdate strategy, the transition is gradual via reconcile().
        """
        self._current_revision += 1
        new_rs = ReplicaSet(
            name=f"{self.name}-rev{self._current_revision}",
            desired_replicas=self.replicas,
            pod_template=new_template,
            revision=self._current_revision,
        )

        # Old ReplicaSet scales down
        old_rs = self.active_replica_set
        old_rs.desired_replicas = 0

        if self.strategy == "Recreate":
            # Kill all old pods immediately, start fresh
            old_rs.current_replicas = 0
            new_rs.current_replicas = self.replicas
        else:
            # RollingUpdate: new RS starts at 0, scales up via reconcile
            new_rs.current_replicas = 0

        self.pod_template = new_template
        self._revisions.append(new_rs)
        return new_rs

    def rollback(self, revision: int | None = None) -> ReplicaSet:
        """Rollback to a previous ReplicaSet revision.

        If revision is None, rolls back to the revision before the current one.
        Creates a new ReplicaSet with the old template (Kubernetes always
        moves forward in revision numbers).
        """
        if len(self._revisions) < 2 and revision is None:
            raise ValueError("No previous revision to rollback to")

        if revision is not None:
            # Find the specified revision
            target = None
            for rs in self._revisions:
                if rs.revision == revision:
                    target = rs
                    break
            if target is None:
                raise ValueError(f"Revision {revision} not found")
        else:
            # Rollback to the second-to-last revision
            target = self._revisions[-2]

        # Create new revision with the old template
        self._current_revision += 1
        rollback_rs = ReplicaSet(
            name=f"{self.name}-rev{self._current_revision}",
            desired_replicas=self.replicas,
            pod_template=target.pod_template,
            revision=self._current_revision,
        )
        rollback_rs.current_replicas = self.replicas

        # Scale down the current active
        self.active_replica_set.desired_replicas = 0
        self.active_replica_set.current_replicas = 0

        self.pod_template = target.pod_template
        self._revisions.append(rollback_rs)
        return rollback_rs

    def get_revision_history(self) -> list[int]:
        """Return list of all revision numbers, oldest first."""
        return [rs.revision for rs in self._revisions]
