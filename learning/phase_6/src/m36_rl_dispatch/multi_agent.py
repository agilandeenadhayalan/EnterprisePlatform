"""
Multi-Agent Reinforcement Learning — independent, shared, and coordinated agents.

WHY THIS MATTERS:
Ride-sharing dispatch involves multiple drivers (agents) operating
simultaneously in the same environment. Each driver's decision affects
the others — if two drivers head to the same pickup, one wastes fuel.
Multi-agent RL techniques address coordination, communication, and
credit assignment challenges that single-agent RL ignores.

Key concepts:
  - Independent Q-learning: each agent learns its own Q-table,
    treating other agents as part of the environment. Simple but
    non-stationary (the environment changes as other agents learn).
  - Shared Q-table: all agents use the same Q-table, assuming
    symmetry. Reduces learning time but may miss agent-specific
    strategies.
  - Communication: agents share information (rewards, observations)
    through a channel. Enables coordination without centralized control.
  - Coordinated agents: combine individual learning with shared
    reward signals to align incentives.
"""

import threading
from .q_learning import QTable, EpsilonGreedyPolicy


class Agent:
    """An individual RL agent with its own Q-table and exploration rate.

    In multi-agent settings, each agent makes independent decisions
    but may share information with other agents.
    """

    def __init__(self, id: str, q_table: QTable = None, epsilon: float = 0.1):
        self.id = id
        self.q_table = q_table or QTable()
        self.epsilon = epsilon
        self._policy = EpsilonGreedyPolicy()

    def select_action(self, state, actions: list):
        """Select action using epsilon-greedy on this agent's Q-table."""
        return self._policy.select(self.q_table, state, actions, self.epsilon)


class SharedQTable:
    """Thread-safe Q-table shared by multiple agents.

    When agents are symmetric (interchangeable), they can share a
    single Q-table. This means experience from any agent benefits all
    agents, dramatically speeding up learning. The lock ensures safe
    concurrent access.
    """

    def __init__(self):
        self._table = QTable()
        self._lock = threading.Lock()

    def get(self, state, action) -> float:
        """Thread-safe get."""
        with self._lock:
            return self._table.get(state, action)

    def set(self, state, action, value: float) -> None:
        """Thread-safe set."""
        with self._lock:
            self._table.set(state, action, value)

    def best_action(self, state, actions: list):
        """Thread-safe best action."""
        with self._lock:
            return self._table.best_action(state, actions)

    def max_value(self, state, actions: list) -> float:
        """Thread-safe max value."""
        with self._lock:
            return self._table.max_value(state, actions)


class IndependentQLearning:
    """Each agent has its own Q-table and learns independently.

    The simplest multi-agent approach: treat other agents as part of
    the environment. Each agent runs standard Q-learning. Simple but
    the environment is non-stationary from each agent's perspective
    (other agents are learning too).
    """

    def __init__(
        self,
        agents: list[Agent],
        env,
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
    ):
        self.agents = {a.id: a for a in agents}
        self.env = env
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor

    def step(
        self,
        agent_id: str,
        state,
        action,
        reward: float,
        next_state,
        next_actions: list,
    ) -> None:
        """Update a single agent's Q-table.

        Standard Q-learning update for the specified agent.
        """
        agent = self.agents[agent_id]
        current_q = agent.q_table.get(state, action)
        max_next_q = agent.q_table.max_value(next_state, next_actions) if next_actions else 0.0
        td_target = reward + self.discount_factor * max_next_q
        new_q = current_q + self.learning_rate * (td_target - current_q)
        agent.q_table.set(state, action, new_q)

    def select_actions(self, states: dict) -> dict:
        """Each agent independently selects an action.

        Args:
            states: dict mapping agent_id to current state

        Returns:
            dict mapping agent_id to selected action
        """
        actions = {}
        for agent_id, state in states.items():
            if agent_id in self.agents:
                valid = self.env.get_valid_actions(state)
                actions[agent_id] = self.agents[agent_id].select_action(state, valid)
        return actions


class CommunicationChannel:
    """Broadcast communication channel for multi-agent coordination.

    Agents can send messages (e.g., their current position, reward
    earned, intended action) and receive messages from other agents.
    This enables decentralized coordination without a central
    controller.
    """

    def __init__(self):
        self._messages: dict[str, list[dict]] = {}  # receiver_id -> messages

    def send(self, sender_id: str, message: dict) -> None:
        """Broadcast a message to all agents.

        The message is added to every agent's inbox (including sender).
        """
        for receiver_id in list(self._messages.keys()):
            self._messages[receiver_id].append({
                "sender": sender_id,
                **message,
            })

    def register(self, agent_id: str) -> None:
        """Register an agent to receive messages."""
        if agent_id not in self._messages:
            self._messages[agent_id] = []

    def receive(self, receiver_id: str) -> list[dict]:
        """Get pending messages for an agent.

        Returns the list of messages and clears the inbox.
        """
        if receiver_id not in self._messages:
            return []
        messages = self._messages[receiver_id]
        self._messages[receiver_id] = []
        return messages

    def clear(self) -> None:
        """Clear all messages for all agents."""
        for key in self._messages:
            self._messages[key] = []


class CoordinatedAgents:
    """Agents that share reward information for coordinated learning.

    Each agent maintains its own Q-table but receives shared reward
    signals through the communication channel. The joint reward
    (mean of individual rewards) encourages cooperative behavior.
    """

    def __init__(
        self,
        agents: list[Agent],
        env,
        channel: CommunicationChannel,
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
    ):
        self.agents = {a.id: a for a in agents}
        self.env = env
        self.channel = channel
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor

        # Register all agents with the channel
        for agent in agents:
            channel.register(agent.id)

    def coordinate_step(self, states: dict, rewards: dict) -> None:
        """Agents share rewards and update Q-tables with shared info.

        Each agent broadcasts its reward, then each agent reads
        all messages and uses the joint reward for its Q-table update.

        Args:
            states: dict mapping agent_id to (state, action, next_state, next_actions)
            rewards: dict mapping agent_id to individual reward
        """
        # Each agent broadcasts its reward
        for agent_id, reward in rewards.items():
            self.channel.send(agent_id, {"reward": reward})

        # Joint reward = mean of all individual rewards
        joint_reward = self.get_joint_reward(rewards)

        # Each agent updates its Q-table using joint reward
        for agent_id, (state, action, next_state, next_actions) in states.items():
            if agent_id not in self.agents:
                continue
            # Receive and clear messages
            self.channel.receive(agent_id)

            agent = self.agents[agent_id]
            current_q = agent.q_table.get(state, action)
            max_next_q = agent.q_table.max_value(next_state, next_actions) if next_actions else 0.0
            td_target = joint_reward + self.discount_factor * max_next_q
            new_q = current_q + self.learning_rate * (td_target - current_q)
            agent.q_table.set(state, action, new_q)

    def get_joint_reward(self, individual_rewards: dict) -> float:
        """Compute joint reward as the mean of individual rewards."""
        if not individual_rewards:
            return 0.0
        return sum(individual_rewards.values()) / len(individual_rewards)
