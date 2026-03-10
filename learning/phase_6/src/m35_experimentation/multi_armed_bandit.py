"""
Multi-Armed Bandit Algorithms — explore/exploit for real-time optimization.

WHY THIS MATTERS:
A/B tests are great for conclusive experiments, but they waste traffic
by sending 50% to a known-worse variant. Bandit algorithms adaptively
shift traffic toward winning variants while still exploring — perfect
for pricing, driver matching, and UI experiments where you want to
minimize regret during the experiment.

Key concepts:
  - Epsilon-Greedy: simple — exploit the best arm (1-epsilon) of the
    time, explore randomly epsilon of the time.
  - UCB1: Upper Confidence Bound — pick the arm with the highest
    optimistic estimate, balancing mean + uncertainty.
  - Thompson Sampling: Bayesian — sample from posterior distributions
    and pick the arm with the highest sample. Naturally balances
    exploration and exploitation.
  - Regret: the cumulative difference between the optimal reward and
    what you actually earned. Good algorithms have sublinear regret.
"""

import random
import math


class BanditArm:
    """A slot machine arm with a hidden true probability.

    Used for simulation: calling pull() returns True with probability
    true_probability. In production, the "pull" would be showing a
    variant to a user and observing the outcome.
    """

    def __init__(self, name: str, true_probability: float):
        self.name = name
        self.true_probability = true_probability

    def pull(self) -> bool:
        """Simulate pulling this arm. Returns True with true_probability."""
        return random.random() < self.true_probability


class EpsilonGreedy:
    """Epsilon-Greedy bandit algorithm.

    With probability epsilon, pick a random arm (explore).
    With probability 1-epsilon, pick the arm with the highest
    empirical mean reward (exploit).

    Simple and effective, but epsilon is fixed — it explores at the
    same rate even after it has strong evidence about which arm is best.
    """

    def __init__(self, arms: list[BanditArm], epsilon: float = 0.1):
        self.arms = arms
        self.epsilon = epsilon
        self._successes = [0] * len(arms)
        self._pulls = [0] * len(arms)

    def select_arm(self) -> int:
        """Select an arm using epsilon-greedy strategy.

        Returns the index of the selected arm.
        """
        if random.random() < self.epsilon:
            return random.randint(0, len(self.arms) - 1)

        # Exploit: pick arm with best empirical mean
        best_arm = 0
        best_mean = -1.0
        for i in range(len(self.arms)):
            if self._pulls[i] == 0:
                return i  # Pull untried arms first
            mean = self._successes[i] / self._pulls[i]
            if mean > best_mean:
                best_mean = mean
                best_arm = i

        return best_arm

    def update(self, arm_index: int, reward: float) -> None:
        """Update arm statistics after observing a reward.

        Args:
            arm_index: which arm was pulled
            reward: observed reward (0 or 1 for Bernoulli)
        """
        self._pulls[arm_index] += 1
        self._successes[arm_index] += reward

    def get_stats(self) -> list[dict]:
        """Return current statistics for each arm."""
        stats = []
        for i, arm in enumerate(self.arms):
            mean = self._successes[i] / self._pulls[i] if self._pulls[i] > 0 else 0.0
            stats.append({
                "name": arm.name,
                "pulls": self._pulls[i],
                "successes": self._successes[i],
                "empirical_mean": mean,
            })
        return stats


class UCB1:
    """Upper Confidence Bound (UCB1) algorithm.

    Selects the arm with the highest upper confidence bound:
      UCB(i) = empirical_mean(i) + sqrt(2 * ln(total_pulls) / pulls(i))

    The second term is the exploration bonus — it's large for arms
    that haven't been pulled much, ensuring they get explored. As an
    arm is pulled more, the bonus shrinks and the empirical mean
    dominates.

    UCB1 has provably optimal regret O(ln(n)).
    """

    def __init__(self, arms: list[BanditArm]):
        self.arms = arms
        self._successes = [0.0] * len(arms)
        self._pulls = [0] * len(arms)
        self._total_pulls = 0

    def select_arm(self) -> int:
        """Select arm with highest UCB score.

        Pulls each arm once first, then uses UCB formula.
        """
        # Pull each arm at least once
        for i in range(len(self.arms)):
            if self._pulls[i] == 0:
                return i

        best_arm = 0
        best_ucb = -1.0
        for i in range(len(self.arms)):
            mean = self._successes[i] / self._pulls[i]
            exploration = math.sqrt(2 * math.log(self._total_pulls) / self._pulls[i])
            ucb = mean + exploration
            if ucb > best_ucb:
                best_ucb = ucb
                best_arm = i

        return best_arm

    def update(self, arm_index: int, reward: float) -> None:
        """Update arm statistics."""
        self._pulls[arm_index] += 1
        self._successes[arm_index] += reward
        self._total_pulls += 1

    def get_stats(self) -> list[dict]:
        """Return current statistics for each arm."""
        stats = []
        for i, arm in enumerate(self.arms):
            mean = self._successes[i] / self._pulls[i] if self._pulls[i] > 0 else 0.0
            stats.append({
                "name": arm.name,
                "pulls": self._pulls[i],
                "successes": self._successes[i],
                "empirical_mean": mean,
            })
        return stats


class ThompsonSampling:
    """Thompson Sampling with Beta-Bernoulli conjugate model.

    Maintains a Beta(alpha, beta) posterior for each arm where:
      alpha = successes + 1 (prior = 1)
      beta = failures + 1 (prior = 1)

    Each round, samples from each arm's Beta posterior and picks the
    arm with the highest sample. This naturally balances exploration
    and exploitation — uncertain arms produce high samples sometimes,
    getting explored, while well-known good arms consistently produce
    high samples.
    """

    def __init__(self, arms: list[BanditArm]):
        self.arms = arms
        self._alphas = [1.0] * len(arms)  # prior successes + 1
        self._betas = [1.0] * len(arms)   # prior failures + 1
        self._pulls = [0] * len(arms)

    def select_arm(self) -> int:
        """Select arm by sampling from Beta posteriors.

        Sample theta_i ~ Beta(alpha_i, beta_i) for each arm,
        then pick argmax(theta_i).

        Uses random.betavariate(alpha, beta).
        """
        samples = [
            random.betavariate(self._alphas[i], self._betas[i])
            for i in range(len(self.arms))
        ]
        return samples.index(max(samples))

    def update(self, arm_index: int, reward: float) -> None:
        """Update Beta posterior for the pulled arm.

        Success (reward=1) increments alpha.
        Failure (reward=0) increments beta.
        """
        self._pulls[arm_index] += 1
        if reward > 0:
            self._alphas[arm_index] += 1
        else:
            self._betas[arm_index] += 1

    def get_stats(self) -> list[dict]:
        """Return current statistics for each arm."""
        stats = []
        for i, arm in enumerate(self.arms):
            alpha = self._alphas[i]
            beta = self._betas[i]
            mean = alpha / (alpha + beta)
            stats.append({
                "name": arm.name,
                "pulls": self._pulls[i],
                "alpha": alpha,
                "beta": beta,
                "posterior_mean": mean,
            })
        return stats


class RegretTracker:
    """Track cumulative regret during a bandit experiment.

    Regret is the difference between the reward you would have earned
    always pulling the optimal arm and what you actually earned.
    Good algorithms have sublinear cumulative regret — the rate of
    regret growth slows over time as the algorithm converges.
    """

    def __init__(self, optimal_arm_index: int, arms: list[BanditArm]):
        self.optimal_arm_index = optimal_arm_index
        self.optimal_prob = arms[optimal_arm_index].true_probability
        self._cumulative_regret = 0.0
        self._history: list[float] = []

    def record(self, arm_index: int, reward: float) -> None:
        """Record one step of regret.

        Regret = optimal_probability - actual_reward
        """
        instant_regret = self.optimal_prob - reward
        self._cumulative_regret += instant_regret
        self._history.append(self._cumulative_regret)

    def cumulative_regret(self) -> float:
        """Return total cumulative regret."""
        return self._cumulative_regret

    def regret_history(self) -> list[float]:
        """Return list of cumulative regret at each time step."""
        return list(self._history)
