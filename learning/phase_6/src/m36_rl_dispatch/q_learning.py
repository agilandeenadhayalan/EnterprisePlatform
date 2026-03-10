"""
Q-Learning and SARSA — tabular reinforcement learning algorithms.

WHY THIS MATTERS:
Q-learning is the foundation of modern RL. It learns the value of
taking action A in state S without needing a model of the environment.
For ride-sharing dispatch, this means learning optimal driver assignment
policies from historical data or simulation, without modeling every
traffic pattern and rider behavior explicitly.

Key concepts:
  - Q-table: Q(s, a) stores the expected cumulative reward of taking
    action a in state s and then following the optimal policy.
  - Bellman equation: Q(s,a) = R + gamma * max_a' Q(s', a')
  - Q-learning (off-policy): updates using max over next-state actions,
    learning the optimal policy regardless of exploration strategy.
  - SARSA (on-policy): updates using the actual next action taken,
    learning the value of the policy being followed.
  - Experience replay: stores transitions and samples random batches,
    breaking temporal correlations and improving sample efficiency.
"""

import random
from collections import deque

from .mdp_environment import Action


class QTable:
    """State-action value table.

    Stores Q(state, action) values as a nested dictionary. Default
    value is 0.0 for unvisited state-action pairs. This is the
    tabular RL approach — works for small, discrete state/action
    spaces like GridWorld.
    """

    def __init__(self):
        self._values: dict = {}

    def get(self, state, action) -> float:
        """Get Q-value for a state-action pair. Returns 0.0 if unvisited."""
        key = (state, action.value if isinstance(action, Action) else action)
        return self._values.get(key, 0.0)

    def set(self, state, action, value: float) -> None:
        """Set Q-value for a state-action pair."""
        key = (state, action.value if isinstance(action, Action) else action)
        self._values[key] = value

    def best_action(self, state, actions: list) -> Action:
        """Return the action with the highest Q-value.

        Breaks ties by returning the first action found.
        """
        best = None
        best_val = float('-inf')
        for a in actions:
            v = self.get(state, a)
            if v > best_val:
                best_val = v
                best = a
        return best

    def max_value(self, state, actions: list) -> float:
        """Return the maximum Q-value over all actions in this state."""
        if not actions:
            return 0.0
        return max(self.get(state, a) for a in actions)


class EpsilonGreedyPolicy:
    """Epsilon-greedy action selection policy.

    With probability epsilon, pick a random action (explore).
    Otherwise pick the greedy action from Q-table (exploit).
    """

    def select(self, q_table: QTable, state, actions: list, epsilon: float) -> Action:
        """Select an action using epsilon-greedy strategy."""
        if not actions:
            raise ValueError("No available actions")
        if random.random() < epsilon:
            return random.choice(actions)
        return q_table.best_action(state, actions)


class QLearningAgent:
    """Q-Learning agent (off-policy TD control).

    Update rule (Bellman equation):
      Q(s, a) <- Q(s, a) + lr * (reward + gamma * max_a' Q(s', a') - Q(s, a))

    Off-policy: the update uses the max over next actions regardless
    of which action the agent actually takes next. This means Q-learning
    converges to the optimal policy even while exploring.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
        epsilon: float = 0.1,
    ):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = QTable()
        self._policy = EpsilonGreedyPolicy()

    def update(self, state, action, reward: float, next_state, next_actions: list) -> None:
        """Update Q-value using the Bellman equation.

        Q(s, a) <- Q(s, a) + lr * (reward + gamma * max_a' Q(s', a') - Q(s, a))
        """
        current_q = self.q_table.get(state, action)
        max_next_q = self.q_table.max_value(next_state, next_actions) if next_actions else 0.0
        td_target = reward + self.discount_factor * max_next_q
        new_q = current_q + self.learning_rate * (td_target - current_q)
        self.q_table.set(state, action, new_q)

    def select_action(self, state, actions: list) -> Action:
        """Select an action using epsilon-greedy policy."""
        return self._policy.select(self.q_table, state, actions, self.epsilon)

    def train_episode(self, env, max_steps: int = 100) -> float:
        """Train for one episode in the environment.

        Args:
            env: GridWorld environment with reset(), step(), get_valid_actions()
            max_steps: maximum steps per episode

        Returns:
            Total reward earned in the episode.
        """
        state = env.reset()
        total_reward = 0.0

        for _ in range(max_steps):
            actions = env.get_valid_actions(state)
            action = self.select_action(state, actions)
            next_state, reward, done = env.step(state, action)
            next_actions = env.get_valid_actions(next_state) if not done else []

            self.update(state, action, reward, next_state, next_actions)

            total_reward += reward
            state = next_state

            if done:
                break

        return total_reward


class SARSAAgent:
    """SARSA agent (on-policy TD control).

    Update rule:
      Q(s, a) <- Q(s, a) + lr * (reward + gamma * Q(s', a') - Q(s, a))

    On-policy: the update uses the actual next action a' that the
    agent selects, not the max. SARSA learns the value of the policy
    it's actually following (including exploration), making it more
    conservative than Q-learning in dangerous environments.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
        epsilon: float = 0.1,
    ):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = QTable()
        self._policy = EpsilonGreedyPolicy()

    def update(self, state, action, reward: float, next_state, next_action) -> None:
        """Update Q-value using SARSA rule.

        Q(s, a) <- Q(s, a) + lr * (reward + gamma * Q(s', a') - Q(s, a))
        Note: uses actual next_action, not max.
        """
        current_q = self.q_table.get(state, action)
        next_q = self.q_table.get(next_state, next_action) if next_action is not None else 0.0
        td_target = reward + self.discount_factor * next_q
        new_q = current_q + self.learning_rate * (td_target - current_q)
        self.q_table.set(state, action, new_q)

    def select_action(self, state, actions: list) -> Action:
        """Select an action using epsilon-greedy policy."""
        return self._policy.select(self.q_table, state, actions, self.epsilon)

    def train_episode(self, env, max_steps: int = 100) -> float:
        """Train for one SARSA episode.

        SARSA requires knowing the next action before updating, so
        the loop is: select a -> step -> select a' -> update -> a = a'.
        """
        state = env.reset()
        actions = env.get_valid_actions(state)
        action = self.select_action(state, actions)
        total_reward = 0.0

        for _ in range(max_steps):
            next_state, reward, done = env.step(state, action)
            total_reward += reward

            if done:
                self.update(state, action, reward, next_state, None)
                break

            next_actions = env.get_valid_actions(next_state)
            next_action = self.select_action(next_state, next_actions)
            self.update(state, action, reward, next_state, next_action)

            state = next_state
            action = next_action

        return total_reward


class ExperienceReplay:
    """Experience replay buffer for off-policy learning.

    Stores (state, action, reward, next_state, done) transitions in
    a fixed-size buffer and samples random mini-batches for training.

    This breaks temporal correlations between consecutive transitions,
    improving learning stability and sample efficiency. Used in DQN
    and most modern deep RL algorithms.
    """

    def __init__(self, buffer_size: int = 1000):
        self._buffer: deque = deque(maxlen=buffer_size)

    def add(self, state, action, reward: float, next_state, done: bool) -> None:
        """Add a transition to the replay buffer."""
        self._buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> list:
        """Sample a random batch of transitions.

        Returns a list of (state, action, reward, next_state, done) tuples.
        If batch_size > buffer size, returns all available transitions.
        """
        batch_size = min(batch_size, len(self._buffer))
        return random.sample(list(self._buffer), batch_size)

    def size(self) -> int:
        """Return the current number of transitions in the buffer."""
        return len(self._buffer)
