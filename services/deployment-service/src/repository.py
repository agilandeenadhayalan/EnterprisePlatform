"""
In-memory deployment repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import Deployment, DeploymentEvent, Environment


class DeploymentRepository:
    """In-memory store for deployments, events, and environments."""

    def __init__(self, seed: bool = False):
        self.deployments: dict[str, Deployment] = {}
        self.events: list[DeploymentEvent] = []
        self.environments: dict[str, Environment] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        deployments = [
            Deployment("dep-001", "auth-service", "v2.1.0", "blue-green", "production", "completed", now, now),
            Deployment("dep-002", "user-service", "v1.5.0", "canary", "staging", "completed", now, now, canary_percentage=100),
            Deployment("dep-003", "payment-service", "v3.0.0", "rolling", "dev", "completed", now, now),
            Deployment("dep-004", "ride-service", "v2.0.0", "canary", "production", "in-progress", now, canary_percentage=25),
            Deployment("dep-005", "notification-service", "v1.2.0", "rolling", "staging", "failed", now),
            Deployment("dep-006", "driver-service", "v1.8.0", "blue-green", "dev", "completed", now, now),
        ]
        for d in deployments:
            self.deployments[d.id] = d

        events = [
            DeploymentEvent("evt-001", "dep-001", "created", {"service": "auth-service", "version": "v2.1.0"}, now),
            DeploymentEvent("evt-002", "dep-001", "completed", {"duration_seconds": 120}, now),
            DeploymentEvent("evt-003", "dep-002", "created", {"service": "user-service", "version": "v1.5.0"}, now),
            DeploymentEvent("evt-004", "dep-002", "completed", {"canary_percentage": 100}, now),
            DeploymentEvent("evt-005", "dep-003", "created", {"service": "payment-service", "version": "v3.0.0"}, now),
            DeploymentEvent("evt-006", "dep-003", "completed", {"duration_seconds": 90}, now),
            DeploymentEvent("evt-007", "dep-004", "created", {"service": "ride-service", "version": "v2.0.0"}, now),
            DeploymentEvent("evt-008", "dep-004", "started", {"canary_percentage": 25}, now),
            DeploymentEvent("evt-009", "dep-005", "created", {"service": "notification-service", "version": "v1.2.0"}, now),
            DeploymentEvent("evt-010", "dep-005", "failed", {"error": "health check timeout"}, now),
            DeploymentEvent("evt-011", "dep-006", "created", {"service": "driver-service", "version": "v1.8.0"}, now),
            DeploymentEvent("evt-012", "dep-006", "completed", {"duration_seconds": 60}, now),
        ]
        self.events.extend(events)

        envs = [
            Environment("dev", "v3.0.0", now, False),
            Environment("staging", "v1.5.0", now, False),
            Environment("production", "v2.1.0", now, False),
        ]
        for e in envs:
            self.environments[e.name] = e

    # ── Deployments ──

    def list_deployments(self) -> list[Deployment]:
        return list(self.deployments.values())

    def get_deployment(self, dep_id: str) -> Deployment | None:
        return self.deployments.get(dep_id)

    def create_deployment(self, data: dict) -> Deployment:
        dep_id = f"dep-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        dep = Deployment(
            id=dep_id,
            service_name=data["service_name"],
            version=data["version"],
            strategy=data["strategy"],
            environment=data["environment"],
            status="pending",
            started_at=now,
            canary_percentage=data.get("canary_percentage"),
        )
        self.deployments[dep.id] = dep
        # Create a "created" event
        evt = DeploymentEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            deployment_id=dep.id,
            action="created",
            details={"service": dep.service_name, "version": dep.version},
            timestamp=now,
        )
        self.events.append(evt)
        return dep

    def rollback_deployment(self, dep_id: str) -> Deployment | None:
        dep = self.deployments.get(dep_id)
        if not dep:
            return None
        dep.status = "rolled-back"
        dep.rolled_back = True
        now = datetime.now(timezone.utc).isoformat()
        dep.completed_at = now
        evt = DeploymentEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            deployment_id=dep.id,
            action="rolled-back",
            details={"reason": "manual rollback"},
            timestamp=now,
        )
        self.events.append(evt)
        return dep

    def promote_deployment(self, dep_id: str) -> Deployment | None:
        """Promote a completed deployment to the next environment."""
        dep = self.deployments.get(dep_id)
        if not dep:
            return None
        promotion_map = {"dev": "staging", "staging": "production"}
        next_env = promotion_map.get(dep.environment)
        if not next_env:
            return None  # already production
        now = datetime.now(timezone.utc).isoformat()
        new_id = f"dep-{uuid.uuid4().hex[:8]}"
        promoted = Deployment(
            id=new_id,
            service_name=dep.service_name,
            version=dep.version,
            strategy=dep.strategy,
            environment=next_env,
            status="pending",
            started_at=now,
            previous_version=dep.version,
        )
        self.deployments[promoted.id] = promoted
        evt = DeploymentEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            deployment_id=promoted.id,
            action="created",
            details={"promoted_from": dep.environment, "service": dep.service_name, "version": dep.version},
            timestamp=now,
        )
        self.events.append(evt)
        return promoted

    # ── Events ──

    def list_events_for_deployment(self, dep_id: str) -> list[DeploymentEvent]:
        return [e for e in self.events if e.deployment_id == dep_id]

    # ── Environments ──

    def list_environments(self) -> list[Environment]:
        return list(self.environments.values())

    # ── Stats ──

    def get_stats(self) -> dict:
        total = len(self.deployments)
        by_status: dict[str, int] = {}
        by_strategy: dict[str, int] = {}
        by_environment: dict[str, int] = {}
        rolled_back_count = 0
        for d in self.deployments.values():
            by_status[d.status] = by_status.get(d.status, 0) + 1
            by_strategy[d.strategy] = by_strategy.get(d.strategy, 0) + 1
            by_environment[d.environment] = by_environment.get(d.environment, 0) + 1
            if d.rolled_back:
                rolled_back_count += 1
        rollback_rate = (rolled_back_count / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "by_status": by_status,
            "by_strategy": by_strategy,
            "by_environment": by_environment,
            "rollback_rate": round(rollback_rate, 2),
        }


REPO_CLASS = DeploymentRepository
repo = DeploymentRepository(seed=True)
