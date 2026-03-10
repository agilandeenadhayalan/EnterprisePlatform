"""
In-memory RL dispatch repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import DispatchState, DispatchAction, DispatchPolicy


class DispatchRepository:
    """In-memory store for dispatch states, actions, and policies."""

    def __init__(self, seed: bool = False):
        self.states: dict[str, DispatchState] = {}
        self.actions: list[DispatchAction] = []
        self.policies: dict[str, DispatchPolicy] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        policies = [
            DispatchPolicy("pol-001", "Greedy Nearest", "greedy",
                           {"strategy": "nearest_driver"}, True, now),
            DispatchPolicy("pol-002", "Q-Learning Dispatch", "q_learning",
                           {"learning_rate": 0.1, "discount": 0.95, "epsilon": 0.1}, False, now),
            DispatchPolicy("pol-003", "DQN Dispatch", "dqn",
                           {"hidden_layers": [64, 32], "batch_size": 32}, False, now),
        ]
        for p in policies:
            self.policies[p.id] = p

        states = [
            DispatchState("state-001", {"grid_size": 10, "zones": 4}, ["driver-001", "driver-002"], ["req-001"], now),
            DispatchState("state-002", {"grid_size": 10, "zones": 4}, ["driver-003"], ["req-002", "req-003"], now),
            DispatchState("state-003", {"grid_size": 10, "zones": 4}, ["driver-001", "driver-004"], ["req-004"], now),
            DispatchState("state-004", {"grid_size": 10, "zones": 4}, ["driver-002"], ["req-005"], now),
            DispatchState("state-005", {"grid_size": 10, "zones": 4}, ["driver-005", "driver-006"], ["req-006", "req-007"], now),
        ]
        for s in states:
            self.states[s.id] = s

        actions = [
            DispatchAction("act-001", "state-001", "driver-001", "req-001", "assign", 0.8, "pol-001", now),
            DispatchAction("act-002", "state-002", "driver-003", "req-002", "assign", 0.6, "pol-001", now),
            DispatchAction("act-003", "state-002", "driver-003", "req-003", "reject", -0.2, "pol-001", now),
            DispatchAction("act-004", "state-003", "driver-001", "req-004", "assign", 0.9, "pol-002", now),
            DispatchAction("act-005", "state-004", "driver-002", "req-005", "assign", 0.7, "pol-002", now),
            DispatchAction("act-006", "state-005", "driver-005", "req-006", "assign", 0.85, "pol-001", now),
            DispatchAction("act-007", "state-005", "driver-006", "req-007", "assign", 0.75, "pol-003", now),
            DispatchAction("act-008", "state-001", "driver-002", "req-001", "wait", 0.1, "pol-003", now),
        ]
        self.actions.extend(actions)

    # ── Policies ──

    def list_policies(self) -> list[DispatchPolicy]:
        return list(self.policies.values())

    def create_policy(self, data: dict) -> DispatchPolicy:
        pid = f"pol-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        policy = DispatchPolicy(
            id=pid,
            name=data["name"],
            algorithm=data["algorithm"],
            parameters=data.get("parameters", {}),
            is_active=False,
            created_at=now,
        )
        self.policies[policy.id] = policy
        return policy

    def activate_policy(self, policy_id: str) -> DispatchPolicy | None:
        policy = self.policies.get(policy_id)
        if not policy:
            return None
        for p in self.policies.values():
            p.is_active = False
        policy.is_active = True
        return policy

    def get_active_policy(self) -> DispatchPolicy | None:
        for p in self.policies.values():
            if p.is_active:
                return p
        return None

    # ── Decide ──

    def decide(self, state: dict, available_drivers: list[str], pending_requests: list[str]) -> DispatchAction | None:
        active_policy = self.get_active_policy()
        if not active_policy:
            return None
        if not available_drivers or not pending_requests:
            return None

        now = datetime.now(timezone.utc).isoformat()
        state_id = f"state-{uuid.uuid4().hex[:8]}"
        ds = DispatchState(state_id, state, available_drivers, pending_requests, now)
        self.states[ds.id] = ds

        driver_id = available_drivers[0]
        request_id = pending_requests[0]

        action = DispatchAction(
            id=f"act-{uuid.uuid4().hex[:8]}",
            state_id=state_id,
            driver_id=driver_id,
            request_id=request_id,
            action_type="assign",
            policy_id=active_policy.id,
            created_at=now,
        )
        self.actions.append(action)
        return action

    # ── Actions ──

    def list_actions(self, policy_id: str | None = None) -> list[DispatchAction]:
        if policy_id:
            return [a for a in self.actions if a.policy_id == policy_id]
        return list(self.actions)

    def get_action(self, action_id: str) -> DispatchAction | None:
        for a in self.actions:
            if a.id == action_id:
                return a
        return None

    def record_reward(self, action_id: str, reward: float) -> DispatchAction | None:
        action = self.get_action(action_id)
        if not action:
            return None
        action.reward = reward
        return action

    # ── Stats ──

    def get_stats(self) -> dict:
        by_policy: dict[str, int] = {}
        total_reward = 0.0
        rewarded_count = 0
        for a in self.actions:
            by_policy[a.policy_id] = by_policy.get(a.policy_id, 0) + 1
            if a.reward is not None:
                total_reward += a.reward
                rewarded_count += 1
        avg_reward = total_reward / rewarded_count if rewarded_count > 0 else 0.0
        active_policy = self.get_active_policy()
        return {
            "total_actions": len(self.actions),
            "by_policy": by_policy,
            "avg_reward": round(avg_reward, 4),
            "active_policy": active_policy.id if active_policy else None,
        }


REPO_CLASS = DispatchRepository
repo = DispatchRepository(seed=True)
