"""
Domain models for the Deployment service.
"""


class Deployment:
    """A deployment record."""

    def __init__(
        self,
        id: str,
        service_name: str,
        version: str,
        strategy: str,
        environment: str,
        status: str,
        started_at: str,
        completed_at: str | None = None,
        rolled_back: bool = False,
        canary_percentage: int | None = None,
        previous_version: str | None = None,
    ):
        self.id = id
        self.service_name = service_name
        self.version = version
        self.strategy = strategy
        self.environment = environment
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.rolled_back = rolled_back
        self.canary_percentage = canary_percentage
        self.previous_version = previous_version

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "version": self.version,
            "strategy": self.strategy,
            "environment": self.environment,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "rolled_back": self.rolled_back,
            "canary_percentage": self.canary_percentage,
            "previous_version": self.previous_version,
        }


class DeploymentEvent:
    """An event in the deployment lifecycle."""

    def __init__(
        self,
        id: str,
        deployment_id: str,
        action: str,
        details: dict,
        timestamp: str,
    ):
        self.id = id
        self.deployment_id = deployment_id
        self.action = action
        self.details = details
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "deployment_id": self.deployment_id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class Environment:
    """An environment with its current deployment state."""

    def __init__(
        self,
        name: str,
        current_version: str,
        last_deployed_at: str,
        is_locked: bool = False,
    ):
        self.name = name
        self.current_version = current_version
        self.last_deployed_at = last_deployed_at
        self.is_locked = is_locked

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "current_version": self.current_version,
            "last_deployed_at": self.last_deployed_at,
            "is_locked": self.is_locked,
        }
