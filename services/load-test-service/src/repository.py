"""
Load Test repository — in-memory scenario, run, and result storage.

Manages load test scenarios, runs, results, and analysis.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import TestScenario, TestRun, TestResult


class LoadTestRepository:
    """In-memory load test storage."""

    def __init__(self):
        self._scenarios: dict[str, TestScenario] = {}
        self._runs: dict[str, TestRun] = {}
        self._results: dict[str, list[TestResult]] = {}  # run_id -> results

    # ── Scenarios ──

    def create_scenario(
        self,
        name: str,
        pattern: str = "ramp",
        target_rps: int = 100,
        duration_seconds: int = 60,
        config: Optional[dict[str, Any]] = None,
    ) -> TestScenario:
        """Create a test scenario."""
        scenario_id = str(uuid.uuid4())
        scenario = TestScenario(
            id=scenario_id,
            name=name,
            pattern=pattern,
            target_rps=target_rps,
            duration_seconds=duration_seconds,
            config=config,
        )
        self._scenarios[scenario_id] = scenario
        return scenario

    def list_scenarios(self) -> list[TestScenario]:
        """List all scenarios."""
        return list(self._scenarios.values())

    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    # ── Runs ──

    def create_run(self, scenario_id: str) -> TestRun:
        """Start a test run."""
        run_id = str(uuid.uuid4())
        run = TestRun(
            id=run_id,
            scenario_id=scenario_id,
            status="running",
        )
        self._runs[run_id] = run
        self._results[run_id] = []
        return run

    def list_runs(self) -> list[TestRun]:
        """List all runs."""
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[TestRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)

    def update_run(self, run_id: str, **fields) -> Optional[TestRun]:
        """Update run fields."""
        run = self._runs.get(run_id)
        if not run:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(run, key):
                setattr(run, key, value)
        return run

    # ── Results ──

    def record_result(
        self,
        run_id: str,
        p50_ms: float = 0.0,
        p95_ms: float = 0.0,
        p99_ms: float = 0.0,
        error_rate: float = 0.0,
        total_requests: int = 0,
        throughput_rps: float = 0.0,
    ) -> Optional[TestResult]:
        """Record results for a run."""
        if run_id not in self._runs:
            return None
        result_id = str(uuid.uuid4())
        result = TestResult(
            id=result_id,
            run_id=run_id,
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            error_rate=error_rate,
            total_requests=total_requests,
            throughput_rps=throughput_rps,
        )
        if run_id not in self._results:
            self._results[run_id] = []
        self._results[run_id].append(result)
        # Also store in run
        self._runs[run_id].results.append(result.to_dict())
        return result

    def get_results(self, run_id: str) -> list[TestResult]:
        """Get results for a run."""
        return self._results.get(run_id, [])

    # ── Analysis ──

    def get_analysis(self, run_id: str) -> Optional[dict]:
        """Get latency analysis for a run."""
        results = self._results.get(run_id, [])
        if not results:
            return {
                "run_id": run_id,
                "num_results": 0,
                "avg_p50_ms": 0.0,
                "avg_p95_ms": 0.0,
                "avg_p99_ms": 0.0,
                "avg_error_rate": 0.0,
                "total_requests": 0,
                "avg_throughput_rps": 0.0,
            }

        n = len(results)
        return {
            "run_id": run_id,
            "num_results": n,
            "avg_p50_ms": round(sum(r.p50_ms for r in results) / n, 2),
            "avg_p95_ms": round(sum(r.p95_ms for r in results) / n, 2),
            "avg_p99_ms": round(sum(r.p99_ms for r in results) / n, 2),
            "avg_error_rate": round(sum(r.error_rate for r in results) / n, 4),
            "total_requests": sum(r.total_requests for r in results),
            "avg_throughput_rps": round(sum(r.throughput_rps for r in results) / n, 2),
        }


# Singleton repository instance
repo = LoadTestRepository()
