"""
Domain models for the RL Dispatch service.
"""


class DispatchState:
    """A snapshot of the dispatch environment state."""

    def __init__(
        self,
        id: str,
        grid_state: dict,
        available_drivers: list,
        pending_requests: list,
        timestamp: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.grid_state = grid_state
        self.available_drivers = available_drivers
        self.pending_requests = pending_requests
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "grid_state": self.grid_state,
            "available_drivers": self.available_drivers,
            "pending_requests": self.pending_requests,
            "timestamp": self.timestamp,
        }


class DispatchAction:
    """A dispatch action (driver-request assignment)."""

    def __init__(
        self,
        id: str,
        state_id: str,
        driver_id: str,
        request_id: str,
        action_type: str,
        reward: float | None = None,
        policy_id: str = "",
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.state_id = state_id
        self.driver_id = driver_id
        self.request_id = request_id
        self.action_type = action_type
        self.reward = reward
        self.policy_id = policy_id
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "state_id": self.state_id,
            "driver_id": self.driver_id,
            "request_id": self.request_id,
            "action_type": self.action_type,
            "reward": self.reward,
            "policy_id": self.policy_id,
            "created_at": self.created_at,
        }


class DispatchPolicy:
    """A dispatch policy configuration."""

    def __init__(
        self,
        id: str,
        name: str,
        algorithm: str,
        parameters: dict,
        is_active: bool = False,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.algorithm = algorithm
        self.parameters = parameters
        self.is_active = is_active
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "algorithm": self.algorithm,
            "parameters": self.parameters,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
