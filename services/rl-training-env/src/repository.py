"""
In-memory RL training environment repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import TrainingEpisode, ReplayBufferEntry, TrainingConfig


class TrainingRepository:
    """In-memory store for training episodes, replay buffer, and configs."""

    def __init__(self, seed: bool = False):
        self.episodes: dict[str, TrainingEpisode] = {}
        self.replay_buffer: list[ReplayBufferEntry] = []
        self.configs: dict[str, TrainingConfig] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        configs = [
            TrainingConfig("cfg-001", "gridworld", 1000, 200, 0.001, 0.99, 1.0, 0.01, 10000),
            TrainingConfig("cfg-002", "taxi", 2000, 500, 0.0005, 0.95, 1.0, 0.05, 50000),
            TrainingConfig("cfg-003", "dispatch_sim", 5000, 1000, 0.0001, 0.99, 1.0, 0.01, 100000),
        ]
        for c in configs:
            self.configs[c.id] = c

        episodes = [
            TrainingEpisode("ep-001", "gridworld", "pol-001", 150, 85.5, 0.1, "completed", now, now),
            TrainingEpisode("ep-002", "gridworld", "pol-001", 120, 92.3, 0.05, "completed", now, now),
            TrainingEpisode("ep-003", "taxi", "pol-002", 350, 45.2, 0.2, "completed", now, now),
            TrainingEpisode("ep-004", "taxi", "pol-002", 200, 0.0, 0.5, "running", now, None),
            TrainingEpisode("ep-005", "dispatch_sim", "pol-003", 500, 120.8, 0.3, "running", now, None),
            TrainingEpisode("ep-006", "dispatch_sim", "pol-003", 50, -10.0, 0.8, "failed", now, now),
        ]
        for e in episodes:
            self.episodes[e.id] = e

        # 15 replay buffer entries
        buffer_entries = [
            ReplayBufferEntry({"pos": [0, 0]}, "right", 0.0, {"pos": [1, 0]}, False),
            ReplayBufferEntry({"pos": [1, 0]}, "right", 0.0, {"pos": [2, 0]}, False),
            ReplayBufferEntry({"pos": [2, 0]}, "down", 0.0, {"pos": [2, 1]}, False),
            ReplayBufferEntry({"pos": [2, 1]}, "down", 1.0, {"pos": [2, 2]}, True),
            ReplayBufferEntry({"pos": [0, 0]}, "down", 0.0, {"pos": [0, 1]}, False),
            ReplayBufferEntry({"pos": [0, 1]}, "right", 0.0, {"pos": [1, 1]}, False),
            ReplayBufferEntry({"pos": [1, 1]}, "right", 0.0, {"pos": [2, 1]}, False),
            ReplayBufferEntry({"pos": [2, 1]}, "down", 1.0, {"pos": [2, 2]}, True),
            ReplayBufferEntry({"zone": 1}, "assign", 0.5, {"zone": 1}, False),
            ReplayBufferEntry({"zone": 1}, "wait", -0.1, {"zone": 1}, False),
            ReplayBufferEntry({"zone": 2}, "assign", 0.8, {"zone": 2}, False),
            ReplayBufferEntry({"zone": 3}, "move", 0.0, {"zone": 2}, False),
            ReplayBufferEntry({"zone": 2}, "assign", 0.9, {"zone": 2}, True),
            ReplayBufferEntry({"taxi": "start"}, "pickup", 1.0, {"taxi": "has_passenger"}, False),
            ReplayBufferEntry({"taxi": "has_passenger"}, "dropoff", 2.0, {"taxi": "done"}, True),
        ]
        self.replay_buffer.extend(buffer_entries)

    # ── Episodes ──

    def start_episode(self, data: dict) -> TrainingEpisode:
        eid = f"ep-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        episode = TrainingEpisode(
            id=eid,
            env_name=data["env_name"],
            policy_id=data["policy_id"],
            steps=0,
            total_reward=0.0,
            epsilon=data.get("epsilon", 1.0),
            status="running",
            started_at=now,
        )
        self.episodes[episode.id] = episode
        return episode

    def list_episodes(self, env_name: str | None = None, status: str | None = None) -> list[TrainingEpisode]:
        episodes = list(self.episodes.values())
        if env_name:
            episodes = [e for e in episodes if e.env_name == env_name]
        if status:
            episodes = [e for e in episodes if e.status == status]
        return episodes

    def get_episode(self, episode_id: str) -> TrainingEpisode | None:
        return self.episodes.get(episode_id)

    def record_step(self, episode_id: str, step_data: dict) -> TrainingEpisode | None:
        episode = self.episodes.get(episode_id)
        if not episode:
            return None
        episode.steps += 1
        episode.total_reward += step_data["reward"]

        # Add to replay buffer
        entry = ReplayBufferEntry(
            state=step_data["state"],
            action=step_data["action"],
            reward=step_data["reward"],
            next_state=step_data["next_state"],
            done=step_data["done"],
        )
        self.replay_buffer.append(entry)

        if step_data["done"]:
            episode.status = "completed"
            episode.completed_at = datetime.now(timezone.utc).isoformat()

        return episode

    def complete_episode(self, episode_id: str) -> TrainingEpisode | None:
        episode = self.episodes.get(episode_id)
        if not episode:
            return None
        episode.status = "completed"
        episode.completed_at = datetime.now(timezone.utc).isoformat()
        return episode

    # ── Configs ──

    def list_configs(self) -> list[TrainingConfig]:
        return list(self.configs.values())

    def create_config(self, data: dict) -> TrainingConfig:
        cid = f"cfg-{uuid.uuid4().hex[:8]}"
        config = TrainingConfig(
            id=cid,
            env_name=data["env_name"],
            max_episodes=data.get("max_episodes", 1000),
            max_steps=data.get("max_steps", 200),
            learning_rate=data.get("learning_rate", 0.001),
            discount_factor=data.get("discount_factor", 0.99),
            epsilon_start=data.get("epsilon_start", 1.0),
            epsilon_end=data.get("epsilon_end", 0.01),
            buffer_size=data.get("buffer_size", 10000),
        )
        self.configs[config.id] = config
        return config

    # ── Stats ──

    def get_stats(self) -> dict:
        episodes = list(self.episodes.values())
        by_status: dict[str, int] = {}
        by_env: dict[str, int] = {}
        total_reward = 0.0
        total_steps = 0
        for e in episodes:
            by_status[e.status] = by_status.get(e.status, 0) + 1
            by_env[e.env_name] = by_env.get(e.env_name, 0) + 1
            total_reward += e.total_reward
            total_steps += e.steps
        n = len(episodes)
        return {
            "total_episodes": n,
            "by_status": by_status,
            "by_env": by_env,
            "avg_reward": round(total_reward / n, 4) if n > 0 else 0.0,
            "avg_steps": round(total_steps / n, 4) if n > 0 else 0.0,
        }


REPO_CLASS = TrainingRepository
repo = TrainingRepository(seed=True)
