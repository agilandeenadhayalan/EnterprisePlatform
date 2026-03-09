"""
Pipeline Stages — DAG-based CI/CD pipeline execution.

WHY THIS MATTERS:
CI/CD pipelines are directed acyclic graphs (DAGs) of stages. Each stage
represents a task (build, test, deploy) with dependencies on other stages.
The pipeline scheduler determines which stages can run in parallel and
which must wait for dependencies.

Key concepts:
  - DAG validation: detecting cycles prevents infinite loops.
  - Topological sort: determines a valid execution order.
  - Parallel execution: stages with no unsatisfied deps run concurrently.
  - Failure propagation: if a stage fails, dependent stages are skipped.

Kahn's algorithm is used for topological sort because it naturally
produces "waves" of parallelizable stages — exactly what a CI/CD
executor needs to maximize throughput.
"""

from collections import deque
from enum import Enum


class StageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStage:
    """A single stage in a CI/CD pipeline.

    Each stage has a name, a list of dependency stage names, a status,
    and a simulated duration.

    Attributes:
        name: Unique stage identifier.
        dependencies: Names of stages that must complete before this one.
        status: Current execution status.
        duration_seconds: Simulated execution time.
    """

    def __init__(
        self,
        name: str,
        dependencies: list[str] | None = None,
        duration_seconds: float = 1.0,
    ):
        self.name = name
        self.dependencies = dependencies or []
        self.status = StageStatus.PENDING
        self.duration_seconds = duration_seconds

    def __repr__(self) -> str:
        return f"PipelineStage('{self.name}', status={self.status.value})"


class Pipeline:
    """A CI/CD pipeline modeled as a DAG of stages.

    The pipeline validates its structure (no cycles, all deps exist),
    computes a topological execution order, and simulates execution
    with failure propagation.

    WHY DAG VALIDATION:
    A cycle in the pipeline graph (A depends on B, B depends on A)
    would cause the pipeline to hang forever. Validating the DAG at
    definition time catches this early.

    WHY TOPOLOGICAL SORT:
    The topological order tells the executor which stages are safe to
    run next. Kahn's algorithm groups stages into "waves" where all
    stages in a wave can run in parallel (their deps are already done).
    """

    def __init__(self):
        self._stages: dict[str, PipelineStage] = {}

    def add_stage(
        self,
        name: str,
        dependencies: list[str] | None = None,
        duration_seconds: float = 1.0,
    ) -> PipelineStage:
        """Add a stage to the pipeline."""
        stage = PipelineStage(name, dependencies, duration_seconds)
        self._stages[name] = stage
        return stage

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the pipeline DAG.

        Checks:
          1. All dependency references point to existing stages.
          2. The graph has no cycles (using DFS-based cycle detection).

        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: list[str] = []

        # Check all deps exist
        for name, stage in self._stages.items():
            for dep in stage.dependencies:
                if dep not in self._stages:
                    errors.append(
                        f"Stage '{name}' depends on unknown stage '{dep}'"
                    )

        if errors:
            return False, errors

        # Check for cycles using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {name: WHITE for name in self._stages}

        def dfs(node: str) -> bool:
            """Returns True if a cycle is found."""
            color[node] = GRAY
            for dep in self._stages[node].dependencies:
                if color[dep] == GRAY:
                    return True  # Back edge = cycle
                if color[dep] == WHITE:
                    if dfs(dep):
                        return True
            color[node] = BLACK
            return False

        for name in self._stages:
            if color[name] == WHITE:
                if dfs(name):
                    errors.append("Pipeline contains a cycle")
                    return False, errors

        return True, errors

    def get_execution_order(self) -> list[list[str]]:
        """Compute parallel execution waves using Kahn's algorithm.

        Returns a list of lists, where each inner list contains stage
        names that can run in parallel (all their deps are in earlier waves).

        This is the core scheduling algorithm for CI/CD executors.
        """
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValueError(f"Invalid pipeline: {errors}")

        # Build adjacency and in-degree maps
        in_degree: dict[str, int] = {name: 0 for name in self._stages}
        dependents: dict[str, list[str]] = {name: [] for name in self._stages}

        for name, stage in self._stages.items():
            for dep in stage.dependencies:
                dependents[dep].append(name)
                in_degree[name] += 1

        # Kahn's algorithm with wave tracking
        waves: list[list[str]] = []
        queue: deque[str] = deque()

        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)

        while queue:
            wave = sorted(queue)  # Sort for deterministic order
            queue.clear()
            waves.append(wave)

            for name in wave:
                for dep_name in dependents[name]:
                    in_degree[dep_name] -= 1
                    if in_degree[dep_name] == 0:
                        queue.append(dep_name)

        return waves

    def get_parallel_groups(self) -> dict[str, list[str]]:
        """Return execution waves labeled as 'wave 1', 'wave 2', etc."""
        waves = self.get_execution_order()
        return {f"wave {i + 1}": wave for i, wave in enumerate(waves)}

    def run(self) -> dict[str, StageStatus]:
        """Simulate pipeline execution with failure propagation.

        Each stage transitions: PENDING -> RUNNING -> SUCCESS.
        If any dependency FAILED or was SKIPPED, the stage is SKIPPED.

        Returns:
            Dict mapping stage name to final status.
        """
        waves = self.get_execution_order()

        for wave in waves:
            for stage_name in wave:
                stage = self._stages[stage_name]

                # Check if any dependency failed or was skipped
                should_skip = False
                for dep_name in stage.dependencies:
                    dep_status = self._stages[dep_name].status
                    if dep_status in (StageStatus.FAILED, StageStatus.SKIPPED):
                        should_skip = True
                        break

                if should_skip:
                    stage.status = StageStatus.SKIPPED
                else:
                    stage.status = StageStatus.RUNNING
                    # Simulate successful execution
                    stage.status = StageStatus.SUCCESS

        return {name: stage.status for name, stage in self._stages.items()}

    def fail_stage(self, name: str) -> None:
        """Manually mark a stage as FAILED (for testing failure propagation)."""
        if name not in self._stages:
            raise KeyError(f"Stage '{name}' not found")
        self._stages[name].status = StageStatus.FAILED

    def run_with_failure(self, failing_stage: str) -> dict[str, StageStatus]:
        """Simulate execution where one specific stage fails.

        All stages before the failing stage succeed. The failing stage
        transitions to FAILED. All downstream stages are SKIPPED.
        """
        waves = self.get_execution_order()

        for wave in waves:
            for stage_name in wave:
                stage = self._stages[stage_name]

                # Check deps
                should_skip = False
                for dep_name in stage.dependencies:
                    dep_status = self._stages[dep_name].status
                    if dep_status in (StageStatus.FAILED, StageStatus.SKIPPED):
                        should_skip = True
                        break

                if should_skip:
                    stage.status = StageStatus.SKIPPED
                elif stage_name == failing_stage:
                    stage.status = StageStatus.FAILED
                else:
                    stage.status = StageStatus.SUCCESS

        return {name: stage.status for name, stage in self._stages.items()}
