"""
Domain models for the RL Training Environment service.
"""


class TrainingEpisode:
    """A training episode."""

    def __init__(
        self,
        id: str,
        env_name: str,
        policy_id: str,
        steps: int,
        total_reward: float,
        epsilon: float,
        status: str,
        started_at: str = "2026-03-01T00:00:00Z",
        completed_at: str | None = None,
    ):
        self.id = id
        self.env_name = env_name
        self.policy_id = policy_id
        self.steps = steps
        self.total_reward = total_reward
        self.epsilon = epsilon
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "env_name": self.env_name,
            "policy_id": self.policy_id,
            "steps": self.steps,
            "total_reward": self.total_reward,
            "epsilon": self.epsilon,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class ReplayBufferEntry:
    """An entry in the replay buffer."""

    def __init__(
        self,
        state: dict,
        action: str,
        reward: float,
        next_state: dict,
        done: bool,
    ):
        self.state = state
        self.action = action
        self.reward = reward
        self.next_state = next_state
        self.done = done

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "next_state": self.next_state,
            "done": self.done,
        }


class TrainingConfig:
    """Training configuration."""

    def __init__(
        self,
        id: str,
        env_name: str,
        max_episodes: int,
        max_steps: int,
        learning_rate: float,
        discount_factor: float,
        epsilon_start: float,
        epsilon_end: float,
        buffer_size: int,
    ):
        self.id = id
        self.env_name = env_name
        self.max_episodes = max_episodes
        self.max_steps = max_steps
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.buffer_size = buffer_size

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "env_name": self.env_name,
            "max_episodes": self.max_episodes,
            "max_steps": self.max_steps,
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon_start": self.epsilon_start,
            "epsilon_end": self.epsilon_end,
            "buffer_size": self.buffer_size,
        }
