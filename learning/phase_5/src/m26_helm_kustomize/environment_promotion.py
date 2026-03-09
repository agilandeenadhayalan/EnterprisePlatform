"""
Environment Promotion Pipeline — controlled progression through environments.

WHY THIS MATTERS:
In enterprise environments, code changes flow through a pipeline of
environments (dev -> staging -> production). Each transition has gates:
automated checks that must pass before promotion is allowed.

This ensures that:
  - Every change is tested in lower environments first.
  - Required quality gates (tests, security scans, approvals) are enforced.
  - There is a clear audit trail of what was promoted, when, and why.

Common gates:
  - All tests pass (automated)
  - Security scan clean (automated)
  - Performance benchmarks met (automated)
  - Change approval board sign-off (manual)
  - Canary deployment healthy for N hours (automated)
"""

from datetime import datetime


class PromotionGate:
    """A single gate that must pass before promotion is allowed.

    Gates can be required or optional. Required gates block promotion
    if they fail. Optional gates generate warnings but allow promotion.

    Attributes:
        name: Human-readable gate name (e.g. "integration-tests").
        check_fn: Callable returning True if gate passes.
        is_required: If True, failure blocks promotion.
    """

    def __init__(self, name: str, check_fn: callable, is_required: bool = True):
        self.name = name
        self.check_fn = check_fn
        self.is_required = is_required

    def check(self) -> bool:
        """Run the gate check and return pass/fail."""
        return self.check_fn()

    def __repr__(self) -> str:
        req = "required" if self.is_required else "optional"
        return f"PromotionGate('{self.name}', {req})"


class PromotionResult:
    """Result of a promotion attempt.

    Attributes:
        success: Whether the promotion succeeded.
        artifact_version: The version that was promoted.
        from_env: Source environment.
        to_env: Target environment.
        failed_gates: List of gate names that failed.
        timestamp: When the promotion was attempted.
    """

    def __init__(
        self,
        success: bool,
        artifact_version: str,
        from_env: str,
        to_env: str,
        failed_gates: list[str] | None = None,
        timestamp: datetime | None = None,
    ):
        self.success = success
        self.artifact_version = artifact_version
        self.from_env = from_env
        self.to_env = to_env
        self.failed_gates = failed_gates or []
        self.timestamp = timestamp or datetime.now()

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"PromotionResult({status}: {self.artifact_version} "
            f"{self.from_env} -> {self.to_env})"
        )


class EnvironmentPipeline:
    """Manages ordered promotion of artifacts through environments.

    The pipeline defines an ordered sequence of environments and the
    gates required for each transition. Artifacts must be promoted
    sequentially (no skipping environments).

    Example pipeline:
        dev -> staging -> production

    Each transition (dev->staging, staging->production) can have its
    own set of gates. Production gates are typically stricter than
    staging gates.

    WHY ORDERED PROMOTION:
    Skipping environments (e.g. dev -> production) is a common source
    of outages. Ordered promotion ensures every change is validated
    in progressively more production-like environments.
    """

    def __init__(self, environments: list[str]):
        if len(environments) < 2:
            raise ValueError("Pipeline must have at least 2 environments")
        self.environments = environments
        self._gates: dict[tuple[str, str], list[PromotionGate]] = {}
        self._versions: dict[str, str | None] = {env: None for env in environments}
        self._history: dict[str, list[PromotionResult]] = {env: [] for env in environments}

    def add_gate(self, from_env: str, to_env: str, gate: PromotionGate) -> None:
        """Add a gate to a specific environment transition.

        Raises:
            ValueError: If the transition is not valid in this pipeline.
        """
        key = (from_env, to_env)
        if from_env not in self.environments or to_env not in self.environments:
            raise ValueError(
                f"Invalid environments: {from_env} and/or {to_env} "
                f"not in {self.environments}"
            )
        from_idx = self.environments.index(from_env)
        to_idx = self.environments.index(to_env)
        if to_idx != from_idx + 1:
            raise ValueError(
                f"Can only add gates for adjacent environments, "
                f"got {from_env} (idx {from_idx}) -> {to_env} (idx {to_idx})"
            )

        if key not in self._gates:
            self._gates[key] = []
        self._gates[key].append(gate)

    def can_promote(
        self, from_env: str, to_env: str
    ) -> tuple[bool, list[str]]:
        """Check if promotion is allowed by evaluating all gates.

        Returns:
            (can_promote, list_of_failed_required_gate_names)
        """
        key = (from_env, to_env)
        gates = self._gates.get(key, [])

        failed: list[str] = []
        for gate in gates:
            if not gate.check():
                if gate.is_required:
                    failed.append(gate.name)

        return len(failed) == 0, failed

    def promote(
        self, artifact_version: str, from_env: str, to_env: str
    ) -> PromotionResult:
        """Attempt to promote an artifact between environments.

        Evaluates all gates for the transition. If any required gate
        fails, the promotion is rejected.

        Returns:
            PromotionResult with success status and details.
        """
        can, failed = self.can_promote(from_env, to_env)

        result = PromotionResult(
            success=can,
            artifact_version=artifact_version,
            from_env=from_env,
            to_env=to_env,
            failed_gates=failed,
        )

        if can:
            self._versions[to_env] = artifact_version

        self._history[to_env].append(result)
        return result

    def get_version(self, env: str) -> str | None:
        """Get the currently deployed version in an environment."""
        return self._versions.get(env)

    def get_history(self, env: str) -> list[PromotionResult]:
        """Get the promotion history for an environment."""
        return self._history.get(env, [])
