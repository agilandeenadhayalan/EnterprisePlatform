"""
Domain models for the Bandit service.
"""


class BanditExperiment:
    """A multi-armed bandit experiment."""

    def __init__(
        self,
        id: str,
        name: str,
        algorithm: str,
        arms: list[dict],
        epsilon: float = 0.1,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.algorithm = algorithm
        self.arms = arms  # list of dicts with name, successes, failures, total_reward, pulls
        self.epsilon = epsilon
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "algorithm": self.algorithm,
            "arms": self.arms,
            "epsilon": self.epsilon,
            "created_at": self.created_at,
        }


class BanditDecision:
    """A recorded bandit decision."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        arm_selected: str,
        reward: float | None = None,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.arm_selected = arm_selected
        self.reward = reward
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "arm_selected": self.arm_selected,
            "reward": self.reward,
            "created_at": self.created_at,
        }
