"""
Deployment Strategies — blue-green, canary, and rolling deployments.

WHY THIS MATTERS:
How you deploy new code determines your blast radius and recovery time.
Each strategy trades off between safety, speed, and resource cost:

  - Blue-Green: Two full environments. Instant switch, instant rollback.
    Cost: 2x infrastructure. Best for critical services.

  - Canary: Gradually shift traffic from old to new. Early detection of
    issues affecting only a small percentage of users.
    Cost: moderate. Best for high-traffic services.

  - Rolling: Update instances in batches. No extra infrastructure needed.
    Cost: minimal. Best for stateless services with many replicas.

All strategies support rollback, which is the most critical capability
in deployment. The fastest way to recover from a bad deploy is to
revert, not to fix-forward.
"""


class BlueGreenDeployment:
    """Blue-Green deployment with instant traffic switching.

    Two identical environments ("blue" and "green") run simultaneously.
    Only one receives production traffic at a time. To deploy:
      1. Deploy new version to the inactive environment.
      2. Run smoke tests against the inactive environment.
      3. Switch traffic to the new environment.
      4. If issues arise, switch back instantly.

    WHY BLUE-GREEN:
    The key advantage is instant rollback: if the new version has problems,
    you switch traffic back to the old environment in seconds, not minutes.
    The cost is running two full environments.
    """

    def __init__(self, initial_version: str):
        self._blue_version = initial_version
        self._green_version: str | None = None
        self._active: str = "blue"  # "blue" or "green"

    @property
    def active_version(self) -> str:
        """The version currently receiving production traffic."""
        if self._active == "blue":
            return self._blue_version
        return self._green_version  # type: ignore

    def deploy(self, version: str) -> str:
        """Deploy a new version to the inactive environment.

        Returns the name of the environment that received the deployment.
        """
        if self._active == "blue":
            self._green_version = version
            return "green"
        else:
            self._blue_version = version
            return "blue"

    def switch_traffic(self) -> str:
        """Switch production traffic to the other environment.

        Returns the name of the newly active environment.
        """
        if self._active == "blue":
            if self._green_version is None:
                raise RuntimeError("No version deployed to green")
            self._active = "green"
        else:
            self._active = "blue"
        return self._active

    def rollback(self) -> str:
        """Rollback by switching traffic back to the previous environment.

        This is the same as switch_traffic() — the beauty of blue-green
        is that rollback is just another traffic switch.

        Returns the name of the active environment after rollback.
        """
        return self.switch_traffic()

    def get_active_version(self) -> str:
        """Return the version currently serving traffic."""
        return self.active_version

    def get_inactive_version(self) -> str | None:
        """Return the version in the inactive environment."""
        if self._active == "blue":
            return self._green_version
        return self._blue_version

    def __repr__(self) -> str:
        return (
            f"BlueGreen(active={self._active}, "
            f"blue={self._blue_version}, green={self._green_version})"
        )


class CanaryDeployment:
    """Canary deployment with gradual traffic shifting.

    Traffic is split between the stable version and the canary (new)
    version. The canary starts with a small percentage and is gradually
    increased as confidence grows.

    Typical canary progression: 5% -> 10% -> 25% -> 50% -> 100%

    WHY CANARY:
    Canary deployments limit the blast radius of a bad deploy. If the
    new version has a bug that causes 500 errors, only 5% of users
    are affected initially. Metrics can detect the issue before the
    canary percentage is increased.
    """

    def __init__(self, stable_version: str, step_size: int = 10):
        self.stable_version = stable_version
        self.canary_version: str | None = None
        self.canary_percentage: int = 0
        self.step_size = step_size

    def deploy_canary(self, version: str) -> None:
        """Deploy a new canary version with initial traffic percentage.

        The canary starts at step_size percent of traffic.
        """
        self.canary_version = version
        self.canary_percentage = self.step_size

    def increase_traffic(self, step: int | None = None) -> int:
        """Increase canary traffic by step_size (or custom step).

        Returns the new canary percentage.
        """
        if self.canary_version is None:
            raise RuntimeError("No canary deployed")

        increment = step if step is not None else self.step_size
        self.canary_percentage = min(100, self.canary_percentage + increment)
        return self.canary_percentage

    def promote(self) -> None:
        """Promote canary to stable (canary becomes the new stable version).

        Traffic shifts to 100% for the canary version, which then
        becomes the stable version.
        """
        if self.canary_version is None:
            raise RuntimeError("No canary to promote")
        self.stable_version = self.canary_version
        self.canary_version = None
        self.canary_percentage = 0

    def rollback(self) -> None:
        """Rollback the canary, sending all traffic back to stable."""
        self.canary_version = None
        self.canary_percentage = 0

    def get_traffic_split(self) -> dict[str, int]:
        """Get current traffic split between stable and canary.

        Returns:
            {"stable": percentage, "canary": percentage}
        """
        return {
            "stable": 100 - self.canary_percentage,
            "canary": self.canary_percentage,
        }

    def __repr__(self) -> str:
        return (
            f"Canary(stable={self.stable_version}, "
            f"canary={self.canary_version}, "
            f"canary_pct={self.canary_percentage}%)"
        )


class RollingDeployment:
    """Rolling deployment that updates instances in batches.

    Instances are updated batch_size at a time. Each batch is updated
    to the target version before the next batch begins. This minimizes
    the number of extra resources needed.

    WHY ROLLING:
    Rolling deployments are the default in Kubernetes because they
    require no extra infrastructure. The trade-off is that during the
    rollout, both old and new versions serve traffic simultaneously,
    which requires backward-compatible changes.
    """

    def __init__(self, instances: list[str], current_version: str, batch_size: int = 1):
        """
        Args:
            instances: List of instance identifiers.
            current_version: Version currently running on all instances.
            batch_size: How many instances to update per batch.
        """
        self.instances = list(instances)
        self.current_version = current_version
        self.target_version: str | None = None
        self.batch_size = batch_size
        self._instance_versions: dict[str, str] = {
            inst: current_version for inst in instances
        }
        self._next_batch_idx: int = 0

    def deploy(self, version: str) -> None:
        """Start a rolling deployment to a new version."""
        self.target_version = version
        self._next_batch_idx = 0

    def deploy_next_batch(self) -> list[str]:
        """Update the next batch of instances.

        Returns the list of instance names that were updated.
        """
        if self.target_version is None:
            raise RuntimeError("No deployment in progress")

        start = self._next_batch_idx
        end = min(start + self.batch_size, len(self.instances))

        updated = []
        for i in range(start, end):
            inst = self.instances[i]
            self._instance_versions[inst] = self.target_version
            updated.append(inst)

        self._next_batch_idx = end

        if self.is_complete():
            self.current_version = self.target_version

        return updated

    def is_complete(self) -> bool:
        """Check if all instances have been updated."""
        if self.target_version is None:
            return True
        return all(
            v == self.target_version for v in self._instance_versions.values()
        )

    def rollback(self) -> None:
        """Rollback all instances to the previous version."""
        for inst in self.instances:
            self._instance_versions[inst] = self.current_version
        self.target_version = None
        self._next_batch_idx = 0

    def get_progress(self) -> dict[str, int | float]:
        """Get the current rollout progress.

        Returns:
            {"updated": count, "total": count, "percent": float}
        """
        if self.target_version is None:
            return {
                "updated": len(self.instances),
                "total": len(self.instances),
                "percent": 100.0,
            }

        updated = sum(
            1 for v in self._instance_versions.values()
            if v == self.target_version
        )
        total = len(self.instances)
        percent = (updated / total * 100) if total > 0 else 0.0
        return {"updated": updated, "total": total, "percent": percent}

    def __repr__(self) -> str:
        prog = self.get_progress()
        return (
            f"Rolling({self.current_version} -> {self.target_version}, "
            f"{prog['updated']}/{prog['total']})"
        )
