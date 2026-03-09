"""
In-memory chaos experiment repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone, timedelta

from models import ChaosExperiment, ChaosRun, SteadyStateHypothesis


# Blast radius dependency mapping
BLAST_RADIUS_MAP = {
    "auth-service": ["auth-service", "api-gateway", "user-service"],
    "payment-service": ["payment-service", "billing-service", "api-gateway"],
    "ride-service": ["ride-service", "driver-service", "matching-service", "api-gateway"],
    "notification-service": ["notification-service", "email-service", "sms-service"],
    "driver-service": ["driver-service", "ride-service", "location-service"],
}

BLAST_RADIUS_IMPACT = {
    "single-service": "Limited to target service only",
    "service-group": "May affect dependent services in the same group",
    "zone": "Affects all services in the target availability zone",
    "cluster": "Affects the entire cluster — maximum blast radius",
}


class ChaosExperimentRepository:
    """In-memory store for chaos experiments, runs, and hypotheses."""

    def __init__(self, seed: bool = False):
        self.experiments: dict[str, ChaosExperiment] = {}
        self.runs: list[ChaosRun] = []
        self.hypotheses: list[SteadyStateHypothesis] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        experiments = [
            ChaosExperiment(
                "exp-001", "Auth Service Latency", "latency-injection", "auth-service",
                "single-service", 300, "completed", now_iso,
                {"delay_ms": 200, "jitter_ms": 50},
            ),
            ChaosExperiment(
                "exp-002", "Payment CPU Stress", "cpu-stress", "payment-service",
                "single-service", 180, "completed", now_iso,
                {"cpu_percent": 80, "workers": 2},
            ),
            ChaosExperiment(
                "exp-003", "Ride Service Pod Kill", "pod-kill", "ride-service",
                "service-group", 60, "draft", now_iso,
                {"kill_count": 1, "grace_period_seconds": 30},
            ),
            ChaosExperiment(
                "exp-004", "Network Partition", "network-partition", "notification-service",
                "zone", 120, "approved", now_iso,
                {"partition_type": "full", "target_zone": "us-east-1a"},
            ),
        ]
        for e in experiments:
            self.experiments[e.id] = e

        # Experiment 1 runs: 2 passed, 2 failed
        good_before = {"error_rate": 0.005, "p99_latency_ms": 150, "availability_percent": 99.99}
        runs_exp1 = [
            ChaosRun(
                "run-001", "exp-001",
                (now - timedelta(hours=24)).isoformat(),
                (now - timedelta(hours=23, minutes=55)).isoformat(),
                good_before,
                {"error_rate": 0.008, "p99_latency_ms": 350, "availability_percent": 99.95},
                "passed",
                {"max_latency_increase_ms": 200, "error_rate_delta": 0.003},
            ),
            ChaosRun(
                "run-002", "exp-001",
                (now - timedelta(hours=20)).isoformat(),
                (now - timedelta(hours=19, minutes=55)).isoformat(),
                good_before,
                {"error_rate": 0.015, "p99_latency_ms": 620, "availability_percent": 99.85},
                "failed",
                {"max_latency_increase_ms": 470, "error_rate_delta": 0.010},
            ),
            ChaosRun(
                "run-003", "exp-001",
                (now - timedelta(hours=16)).isoformat(),
                (now - timedelta(hours=15, minutes=55)).isoformat(),
                good_before,
                {"error_rate": 0.007, "p99_latency_ms": 300, "availability_percent": 99.96},
                "passed",
                {"max_latency_increase_ms": 150, "error_rate_delta": 0.002},
            ),
            ChaosRun(
                "run-004", "exp-001",
                (now - timedelta(hours=12)).isoformat(),
                (now - timedelta(hours=11, minutes=55)).isoformat(),
                good_before,
                {"error_rate": 0.020, "p99_latency_ms": 750, "availability_percent": 99.80},
                "failed",
                {"max_latency_increase_ms": 600, "error_rate_delta": 0.015},
            ),
        ]
        self.runs.extend(runs_exp1)

        # Experiment 2 runs: 3 passed, 1 failed
        good_before2 = {"error_rate": 0.003, "p99_latency_ms": 100, "availability_percent": 99.99}
        runs_exp2 = [
            ChaosRun(
                "run-005", "exp-002",
                (now - timedelta(hours=10)).isoformat(),
                (now - timedelta(hours=9, minutes=57)).isoformat(),
                good_before2,
                {"error_rate": 0.005, "p99_latency_ms": 180, "availability_percent": 99.97},
                "passed",
                {"cpu_spike_percent": 82, "error_rate_delta": 0.002},
            ),
            ChaosRun(
                "run-006", "exp-002",
                (now - timedelta(hours=8)).isoformat(),
                (now - timedelta(hours=7, minutes=57)).isoformat(),
                good_before2,
                {"error_rate": 0.004, "p99_latency_ms": 160, "availability_percent": 99.98},
                "passed",
                {"cpu_spike_percent": 79, "error_rate_delta": 0.001},
            ),
            ChaosRun(
                "run-007", "exp-002",
                (now - timedelta(hours=6)).isoformat(),
                (now - timedelta(hours=5, minutes=57)).isoformat(),
                good_before2,
                {"error_rate": 0.012, "p99_latency_ms": 550, "availability_percent": 99.88},
                "failed",
                {"cpu_spike_percent": 95, "error_rate_delta": 0.009},
            ),
            ChaosRun(
                "run-008", "exp-002",
                (now - timedelta(hours=4)).isoformat(),
                (now - timedelta(hours=3, minutes=57)).isoformat(),
                good_before2,
                {"error_rate": 0.006, "p99_latency_ms": 200, "availability_percent": 99.95},
                "passed",
                {"cpu_spike_percent": 81, "error_rate_delta": 0.003},
            ),
        ]
        self.runs.extend(runs_exp2)

        # Steady state hypotheses for exp-001 and exp-002
        hypotheses = [
            SteadyStateHypothesis("hyp-001", "exp-001", "error_rate", "lt", 0.01, "Error rate stays below 1%"),
            SteadyStateHypothesis("hyp-002", "exp-001", "p99_latency_ms", "lt", 500, "P99 latency stays below 500ms"),
            SteadyStateHypothesis("hyp-003", "exp-001", "availability_percent", "gte", 99.9, "Availability stays above 99.9%"),
            SteadyStateHypothesis("hyp-004", "exp-002", "error_rate", "lt", 0.01, "Error rate stays below 1%"),
            SteadyStateHypothesis("hyp-005", "exp-002", "p99_latency_ms", "lt", 500, "P99 latency stays below 500ms"),
            SteadyStateHypothesis("hyp-006", "exp-002", "availability_percent", "gte", 99.9, "Availability stays above 99.9%"),
        ]
        self.hypotheses.extend(hypotheses)

    # ── Experiments ──

    def list_experiments(self) -> list[ChaosExperiment]:
        return list(self.experiments.values())

    def get_experiment(self, exp_id: str) -> ChaosExperiment | None:
        return self.experiments.get(exp_id)

    def create_experiment(self, data: dict) -> ChaosExperiment:
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        exp = ChaosExperiment(
            id=exp_id,
            name=data["name"],
            experiment_type=data["experiment_type"],
            target_service=data["target_service"],
            blast_radius=data.get("blast_radius", "single-service"),
            duration_seconds=data.get("duration_seconds", 60),
            status=data.get("status", "draft"),
            created_at=now,
            parameters=data.get("parameters", {}),
        )
        self.experiments[exp.id] = exp
        return exp

    # ── Runs ──

    def start_run(self, exp_id: str) -> ChaosRun | None:
        exp = self.experiments.get(exp_id)
        if not exp:
            return None
        now = datetime.now(timezone.utc).isoformat()
        # Simulate initial steady state
        steady_state_before = {
            "error_rate": 0.005,
            "p99_latency_ms": 120,
            "availability_percent": 99.99,
        }
        run = ChaosRun(
            id=f"run-{uuid.uuid4().hex[:8]}",
            experiment_id=exp.id,
            started_at=now,
            steady_state_before=steady_state_before,
            result="pending",
        )
        self.runs.append(run)
        return run

    def list_runs_for_experiment(self, exp_id: str) -> list[ChaosRun]:
        return [r for r in self.runs if r.experiment_id == exp_id]

    # ── Blast Radius ──

    def get_blast_radius(self, exp_id: str) -> dict | None:
        exp = self.experiments.get(exp_id)
        if not exp:
            return None
        affected = BLAST_RADIUS_MAP.get(exp.target_service, [exp.target_service])
        impact = BLAST_RADIUS_IMPACT.get(exp.blast_radius, "Unknown impact scope")
        return {
            "experiment_id": exp.id,
            "blast_radius": exp.blast_radius,
            "target_service": exp.target_service,
            "affected_services": affected,
            "estimated_impact": impact,
        }

    # ── Verification ──

    def verify_steady_state(self, exp_id: str) -> dict | None:
        exp = self.experiments.get(exp_id)
        if not exp:
            return None
        hypotheses = [h for h in self.hypotheses if h.experiment_id == exp_id]
        runs = self.list_runs_for_experiment(exp_id)
        if not runs:
            return {"passed": True, "results": []}
        latest_run = runs[-1]
        after = latest_run.steady_state_after
        if not after:
            return {"passed": True, "results": []}

        results = []
        all_passed = True
        for hyp in hypotheses:
            actual_val = after.get(hyp.metric_name, 0)
            passed = self._check_operator(actual_val, hyp.operator, hyp.threshold)
            if not passed:
                all_passed = False
            results.append({
                "metric": hyp.metric_name,
                "expected": f"{hyp.operator} {hyp.threshold}",
                "actual": actual_val,
                "passed": passed,
            })
        return {"passed": all_passed, "results": results}

    def _check_operator(self, actual: float, operator: str, threshold: float) -> bool:
        if operator == "lt":
            return actual < threshold
        elif operator == "gt":
            return actual > threshold
        elif operator == "eq":
            return actual == threshold
        elif operator == "lte":
            return actual <= threshold
        elif operator == "gte":
            return actual >= threshold
        return False

    # ── Stats ──

    def get_stats(self) -> dict:
        total_exp = len(self.experiments)
        total_runs = len(self.runs)
        by_type: dict[str, int] = {}
        for exp in self.experiments.values():
            by_type[exp.experiment_type] = by_type.get(exp.experiment_type, 0) + 1
        by_result: dict[str, int] = {}
        for run in self.runs:
            by_result[run.result] = by_result.get(run.result, 0) + 1
        passed = by_result.get("passed", 0)
        completed_runs = passed + by_result.get("failed", 0)
        pass_rate = round(passed / completed_runs * 100, 2) if completed_runs > 0 else 0.0
        return {
            "total_experiments": total_exp,
            "total_runs": total_runs,
            "pass_rate": pass_rate,
            "by_type": by_type,
            "by_result": by_result,
        }


REPO_CLASS = ChaosExperimentRepository
repo = ChaosExperimentRepository(seed=True)
