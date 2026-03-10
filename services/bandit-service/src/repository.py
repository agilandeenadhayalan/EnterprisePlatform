"""
In-memory bandit repository with pre-seeded data.
"""

import math
import random
import uuid
from datetime import datetime, timezone

from models import BanditExperiment, BanditDecision


class BanditRepository:
    """In-memory store for bandit experiments and decisions."""

    def __init__(self, seed: bool = False):
        self.bandits: dict[str, BanditExperiment] = {}
        self.decisions: list[BanditDecision] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        bandits = [
            BanditExperiment(
                "bandit-001", "Homepage CTA", "epsilon_greedy",
                [
                    {"name": "red_button", "successes": 45, "failures": 155, "total_reward": 45.0, "pulls": 200},
                    {"name": "blue_button", "successes": 62, "failures": 138, "total_reward": 62.0, "pulls": 200},
                    {"name": "green_button", "successes": 38, "failures": 162, "total_reward": 38.0, "pulls": 200},
                ],
                epsilon=0.1, created_at=now,
            ),
            BanditExperiment(
                "bandit-002", "Pricing Display", "ucb1",
                [
                    {"name": "monthly", "successes": 30, "failures": 70, "total_reward": 30.0, "pulls": 100},
                    {"name": "annual", "successes": 55, "failures": 45, "total_reward": 55.0, "pulls": 100},
                    {"name": "lifetime", "successes": 15, "failures": 85, "total_reward": 15.0, "pulls": 100},
                    {"name": "trial", "successes": 40, "failures": 60, "total_reward": 40.0, "pulls": 100},
                ],
                epsilon=0.1, created_at=now,
            ),
            BanditExperiment(
                "bandit-003", "Email Subject Line", "thompson_sampling",
                [
                    {"name": "urgent", "successes": 25, "failures": 75, "total_reward": 25.0, "pulls": 100},
                    {"name": "friendly", "successes": 35, "failures": 65, "total_reward": 35.0, "pulls": 100},
                    {"name": "formal", "successes": 20, "failures": 80, "total_reward": 20.0, "pulls": 100},
                ],
                epsilon=0.1, created_at=now,
            ),
        ]
        for b in bandits:
            self.bandits[b.id] = b

        decisions = [
            BanditDecision("dec-001", "bandit-001", "blue_button", 1.0, now),
            BanditDecision("dec-002", "bandit-001", "red_button", 0.0, now),
            BanditDecision("dec-003", "bandit-001", "blue_button", 1.0, now),
            BanditDecision("dec-004", "bandit-002", "annual", 1.0, now),
            BanditDecision("dec-005", "bandit-002", "monthly", 0.0, now),
            BanditDecision("dec-006", "bandit-002", "annual", 1.0, now),
            BanditDecision("dec-007", "bandit-003", "friendly", 1.0, now),
            BanditDecision("dec-008", "bandit-003", "urgent", 0.0, now),
            BanditDecision("dec-009", "bandit-003", "friendly", 1.0, now),
            BanditDecision("dec-010", "bandit-003", "formal", 0.0, now),
        ]
        self.decisions.extend(decisions)

    # ── CRUD ──

    def list_bandits(self) -> list[BanditExperiment]:
        return list(self.bandits.values())

    def get_bandit(self, bandit_id: str) -> BanditExperiment | None:
        return self.bandits.get(bandit_id)

    def create_bandit(self, data: dict) -> BanditExperiment:
        bid = f"bandit-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        arms = data.get("arms", [])
        for arm in arms:
            arm.setdefault("successes", 0)
            arm.setdefault("failures", 0)
            arm.setdefault("total_reward", 0.0)
            arm.setdefault("pulls", 0)
        bandit = BanditExperiment(
            id=bid,
            name=data["name"],
            algorithm=data["algorithm"],
            arms=arms,
            epsilon=data.get("epsilon", 0.1),
            created_at=now,
        )
        self.bandits[bandit.id] = bandit
        return bandit

    # ── Pull (arm selection) ──

    def pull(self, bandit_id: str) -> str | None:
        bandit = self.bandits.get(bandit_id)
        if not bandit:
            return None
        if not bandit.arms:
            return None

        arm_name = self._select_arm(bandit)

        now = datetime.now(timezone.utc).isoformat()
        decision = BanditDecision(
            id=f"dec-{uuid.uuid4().hex[:8]}",
            experiment_id=bandit_id,
            arm_selected=arm_name,
            created_at=now,
        )
        self.decisions.append(decision)
        return arm_name

    def _select_arm(self, bandit: BanditExperiment) -> str:
        if bandit.algorithm == "epsilon_greedy":
            return self._epsilon_greedy(bandit)
        elif bandit.algorithm == "ucb1":
            return self._ucb1(bandit)
        elif bandit.algorithm == "thompson_sampling":
            return self._thompson_sampling(bandit)
        else:
            return bandit.arms[0]["name"]

    def _epsilon_greedy(self, bandit: BanditExperiment) -> str:
        if random.random() < bandit.epsilon:
            return random.choice(bandit.arms)["name"]
        best_arm = max(
            bandit.arms,
            key=lambda a: a["total_reward"] / a["pulls"] if a["pulls"] > 0 else 0.0,
        )
        return best_arm["name"]

    def _ucb1(self, bandit: BanditExperiment) -> str:
        total_pulls = sum(a["pulls"] for a in bandit.arms)
        if total_pulls == 0:
            return random.choice(bandit.arms)["name"]

        best_arm = None
        best_score = -1.0
        for arm in bandit.arms:
            if arm["pulls"] == 0:
                return arm["name"]
            mean = arm["total_reward"] / arm["pulls"]
            exploration = math.sqrt(2 * math.log(total_pulls) / arm["pulls"])
            score = mean + exploration
            if score > best_score:
                best_score = score
                best_arm = arm
        return best_arm["name"]

    def _thompson_sampling(self, bandit: BanditExperiment) -> str:
        best_arm = None
        best_sample = -1.0
        for arm in bandit.arms:
            alpha = arm["successes"] + 1
            beta = arm["failures"] + 1
            sample = random.betavariate(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                best_arm = arm
        return best_arm["name"]

    # ── Reward ──

    def record_reward(self, bandit_id: str, arm_name: str, reward: float, success: bool) -> dict | None:
        bandit = self.bandits.get(bandit_id)
        if not bandit:
            return None
        arm = None
        for a in bandit.arms:
            if a["name"] == arm_name:
                arm = a
                break
        if not arm:
            return "arm_not_found"
        arm["pulls"] += 1
        arm["total_reward"] += reward
        if success:
            arm["successes"] += 1
        else:
            arm["failures"] += 1
        return arm

    # ── Decisions ──

    def list_decisions(self, bandit_id: str) -> list[BanditDecision]:
        return [d for d in self.decisions if d.experiment_id == bandit_id]

    # ── Stats ──

    def get_stats(self, bandit_id: str) -> dict | None:
        bandit = self.bandits.get(bandit_id)
        if not bandit:
            return None
        arm_stats = []
        for arm in bandit.arms:
            pulls = arm["pulls"]
            arm_stats.append({
                "name": arm["name"],
                "successes": arm["successes"],
                "failures": arm["failures"],
                "total_reward": arm["total_reward"],
                "pulls": pulls,
                "success_rate": arm["successes"] / pulls if pulls > 0 else 0.0,
                "avg_reward": arm["total_reward"] / pulls if pulls > 0 else 0.0,
            })
        return {"experiment_id": bandit_id, "arms": arm_stats}

    # ── Reset ──

    def reset(self, bandit_id: str) -> BanditExperiment | None:
        bandit = self.bandits.get(bandit_id)
        if not bandit:
            return None
        for arm in bandit.arms:
            arm["successes"] = 0
            arm["failures"] = 0
            arm["total_reward"] = 0.0
            arm["pulls"] = 0
        self.decisions = [d for d in self.decisions if d.experiment_id != bandit_id]
        return bandit


REPO_CLASS = BanditRepository
repo = BanditRepository(seed=True)
