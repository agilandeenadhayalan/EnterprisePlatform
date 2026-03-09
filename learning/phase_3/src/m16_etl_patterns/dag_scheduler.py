"""
DAG-Based Task Scheduling
============================

ETL/ELT pipelines are modeled as Directed Acyclic Graphs (DAGs),
where each node is a task and edges represent dependencies.

KEY CONCEPTS:

1. **Task** — A unit of work (extract, transform, load, validate).
   Each task declares its dependencies.

2. **DAG** — A directed acyclic graph of tasks. "Acyclic" means no
   circular dependencies (A depends on B depends on A is forbidden).

3. **Topological Sort** — Orders tasks so that every task runs after
   all its dependencies. Multiple valid orderings may exist.

4. **Parallel Execution** — Tasks without mutual dependencies can
   run concurrently (e.g., extract from 3 sources simultaneously).

REAL IMPLEMENTATIONS:
- Apache Airflow — The most popular DAG scheduler for data pipelines.
- Dagster — Type-safe, testable pipelines with IO managers.
- Prefect — Dynamic workflows with Python-native API.
- dbt — SQL-based DAGs for transformation (ELT pattern).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_name: str
    status: TaskStatus
    output: Any = None
    error: str | None = None
    execution_order: int = 0


class Task:
    """
    A single unit of work in a DAG.

    Each task has a name, a list of dependencies (other task names),
    and an execute function that performs the actual work.
    """

    def __init__(
        self,
        name: str,
        dependencies: list[str] | None = None,
        execute_fn: Callable[[], Any] | None = None,
    ) -> None:
        self.name = name
        self.dependencies = dependencies or []
        self._execute_fn = execute_fn or (lambda: f"{name} completed")
        self.status = TaskStatus.PENDING
        self.result: Any = None

    def execute(self) -> Any:
        """Run the task's execute function."""
        self.status = TaskStatus.RUNNING
        try:
            self.result = self._execute_fn()
            self.status = TaskStatus.COMPLETED
            return self.result
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)
            raise


class DAG:
    """
    Directed Acyclic Graph of tasks.

    Manages task registration, dependency validation, topological
    ordering, and execution.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._tasks: dict[str, Task] = {}

    @property
    def tasks(self) -> dict[str, Task]:
        return dict(self._tasks)

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def add_task(self, task: Task) -> None:
        """Add a task to the DAG."""
        if task.name in self._tasks:
            raise ValueError(f"Task '{task.name}' already exists in DAG '{self.name}'")
        self._tasks[task.name] = task

    def detect_cycles(self) -> list[str] | None:
        """
        Detect cycles using DFS. Returns the cycle path if found, None if no cycles.

        A cycle means there's a circular dependency (A -> B -> C -> A),
        which would make execution impossible.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {name: WHITE for name in self._tasks}
        parent: dict[str, str | None] = {name: None for name in self._tasks}

        def dfs(node: str) -> list[str] | None:
            color[node] = GRAY
            task = self._tasks[node]
            for dep in task.dependencies:
                if dep not in self._tasks:
                    continue
                if color[dep] == GRAY:
                    # Found a cycle — reconstruct path
                    cycle = [dep, node]
                    current = node
                    while parent.get(current) and parent[current] != dep:
                        current = parent[current]
                        cycle.append(current)
                    return list(reversed(cycle))
                if color[dep] == WHITE:
                    parent[dep] = node
                    result = dfs(dep)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for name in self._tasks:
            if color[name] == WHITE:
                result = dfs(name)
                if result:
                    return result
        return None

    def topological_sort(self) -> list[str]:
        """
        Return tasks in topological order (dependencies before dependents).

        Uses Kahn's algorithm (BFS-based):
        1. Compute in-degree for each task.
        2. Start with tasks that have in-degree 0 (no dependencies).
        3. Process each, reducing in-degree of its dependents.
        4. Repeat until all tasks are processed.
        """
        cycle = self.detect_cycles()
        if cycle:
            raise ValueError(f"DAG has a cycle: {' -> '.join(cycle)}")

        # Compute in-degree (number of unresolved dependencies)
        in_degree: dict[str, int] = {name: 0 for name in self._tasks}
        # Build reverse adjacency: task -> list of tasks that depend on it
        dependents: dict[str, list[str]] = {name: [] for name in self._tasks}

        for name, task in self._tasks.items():
            for dep in task.dependencies:
                if dep in self._tasks:
                    in_degree[name] += 1
                    dependents[dep].append(name)

        # Start with tasks that have no dependencies
        queue: deque[str] = deque(
            name for name, degree in in_degree.items() if degree == 0
        )
        result: list[str] = []

        while queue:
            name = queue.popleft()
            result.append(name)
            for dependent in dependents[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._tasks):
            raise ValueError("DAG has unresolvable dependencies")

        return result

    def execute(self) -> list[TaskResult]:
        """
        Execute all tasks in topological order.

        If a task fails, its downstream dependents are skipped.
        """
        order = self.topological_sort()
        results: list[TaskResult] = []
        failed_tasks: set[str] = set()

        for i, name in enumerate(order):
            task = self._tasks[name]

            # Check if any dependency failed
            if any(dep in failed_tasks for dep in task.dependencies):
                task.status = TaskStatus.SKIPPED
                results.append(TaskResult(
                    task_name=name,
                    status=TaskStatus.SKIPPED,
                    error="Upstream dependency failed",
                    execution_order=i,
                ))
                failed_tasks.add(name)
                continue

            try:
                output = task.execute()
                results.append(TaskResult(
                    task_name=name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    execution_order=i,
                ))
            except Exception as e:
                failed_tasks.add(name)
                results.append(TaskResult(
                    task_name=name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    execution_order=i,
                ))

        return results

    def parallel_groups(self) -> list[list[str]]:
        """
        Group tasks into parallel execution levels.

        Tasks in the same level have no dependencies on each other
        and can run concurrently. Each level depends on the previous level.

        Example:
            Level 0: [extract_a, extract_b]  (no deps, run in parallel)
            Level 1: [transform]             (depends on extract_a, extract_b)
            Level 2: [load]                  (depends on transform)
        """
        order = self.topological_sort()
        levels: dict[str, int] = {}

        for name in order:
            task = self._tasks[name]
            if not task.dependencies:
                levels[name] = 0
            else:
                dep_levels = [
                    levels.get(dep, 0) for dep in task.dependencies
                    if dep in self._tasks
                ]
                levels[name] = max(dep_levels) + 1 if dep_levels else 0

        # Group by level
        max_level = max(levels.values()) if levels else 0
        groups: list[list[str]] = [[] for _ in range(max_level + 1)]
        for name, level in levels.items():
            groups[level].append(name)
        return groups
