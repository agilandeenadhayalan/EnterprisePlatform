"""
Tests for M36: Reinforcement Learning for Dispatch — MDPs, Q-learning, multi-agent.
"""

import random
import pytest

from m36_rl_dispatch.mdp_environment import State, Action, Transition, MDP, GridWorld
from m36_rl_dispatch.q_learning import (
    QTable,
    EpsilonGreedyPolicy,
    QLearningAgent,
    SARSAAgent,
    ExperienceReplay,
)
from m36_rl_dispatch.multi_agent import (
    Agent,
    SharedQTable,
    IndependentQLearning,
    CommunicationChannel,
    CoordinatedAgents,
)


# ── State & Action ──


class TestStateAction:
    def test_state_creation(self):
        """State stores id, name, and default attributes."""
        s = State(id="s0", name="Start")
        assert s.id == "s0"
        assert s.name == "Start"
        assert s.is_terminal is False
        assert s.reward == 0.0

    def test_terminal_state(self):
        """Terminal state is marked correctly."""
        s = State(id="goal", name="Goal", is_terminal=True, reward=10.0)
        assert s.is_terminal is True
        assert s.reward == 10.0

    def test_action_values(self):
        """Action enum has four directions."""
        assert len(Action) == 4
        assert Action.UP.value == "up"
        assert Action.DOWN.value == "down"
        assert Action.LEFT.value == "left"
        assert Action.RIGHT.value == "right"


# ── MDP ──


class TestMDP:
    def test_add_state_and_check(self):
        """MDP tracks added states."""
        mdp = MDP()
        mdp.add_state(State("s0", "Start"))
        assert not mdp.is_terminal("s0")

    def test_terminal_check(self):
        """MDP correctly identifies terminal states."""
        mdp = MDP()
        mdp.add_state(State("goal", "Goal", is_terminal=True))
        assert mdp.is_terminal("goal")

    def test_add_transition(self):
        """MDP stores transitions."""
        mdp = MDP()
        mdp.add_state(State("s0", "Start"))
        mdp.add_state(State("s1", "Next"))
        t = Transition("s0", Action.RIGHT, "s1", 1.0, -1.0)
        mdp.add_transition(t)
        transitions = mdp.get_transitions("s0", Action.RIGHT)
        assert len(transitions) == 1
        assert transitions[0].next_state_id == "s1"

    def test_get_actions(self):
        """MDP returns available actions for a state."""
        mdp = MDP()
        mdp.add_state(State("s0", "Start"))
        t = Transition("s0", Action.UP, "s0", 1.0, 0.0)
        mdp.add_transition(t)
        actions = mdp.get_actions("s0")
        assert Action.UP in actions

    def test_no_transitions(self):
        """Unknown state returns empty transitions."""
        mdp = MDP()
        assert mdp.get_transitions("unknown", Action.UP) == []

    def test_unknown_state_not_terminal(self):
        """Unknown state is not terminal."""
        mdp = MDP()
        assert mdp.is_terminal("nonexistent") is False


# ── GridWorld ──


class TestGridWorld:
    def _make_grid(self):
        return GridWorld(
            rows=4, cols=4,
            walls=[(1, 1)],
            goals={(3, 3): 10.0},
            traps={(2, 3): -5.0},
        )

    def test_reset(self):
        """Reset returns (0, 0)."""
        env = self._make_grid()
        pos = env.reset()
        assert pos == (0, 0)

    def test_step_right(self):
        """Moving RIGHT increments column."""
        env = self._make_grid()
        next_s, reward, done = env.step((0, 0), Action.RIGHT)
        assert next_s == (0, 1)
        assert done is False

    def test_step_down(self):
        """Moving DOWN increments row."""
        env = self._make_grid()
        next_s, reward, done = env.step((0, 0), Action.DOWN)
        assert next_s == (1, 0)
        assert done is False

    def test_step_clips_to_bounds(self):
        """Moving beyond grid bounds clips to edge."""
        env = self._make_grid()
        next_s, _, _ = env.step((0, 0), Action.UP)
        assert next_s == (0, 0)
        next_s, _, _ = env.step((0, 0), Action.LEFT)
        assert next_s == (0, 0)

    def test_wall_blocks_movement(self):
        """Walls block movement — agent stays in place."""
        env = self._make_grid()
        next_s, _, _ = env.step((0, 1), Action.DOWN)
        assert next_s == (0, 1)  # (1,1) is a wall

    def test_goal_terminates(self):
        """Reaching a goal gives positive reward and terminates."""
        env = self._make_grid()
        next_s, reward, done = env.step((3, 2), Action.RIGHT)
        assert next_s == (3, 3)
        assert reward == 10.0
        assert done is True

    def test_trap_terminates(self):
        """Stepping on a trap gives negative reward and terminates."""
        env = self._make_grid()
        next_s, reward, done = env.step((2, 2), Action.RIGHT)
        assert next_s == (2, 3)
        assert reward == -5.0
        assert done is True

    def test_step_penalty(self):
        """Normal steps have a small negative reward."""
        env = self._make_grid()
        _, reward, _ = env.step((0, 0), Action.RIGHT)
        assert reward < 0  # Step penalty

    def test_valid_actions(self):
        """All four actions are valid from any position."""
        env = self._make_grid()
        actions = env.get_valid_actions((0, 0))
        assert len(actions) == 4

    def test_render_shows_walls(self):
        """Render produces ASCII grid with walls."""
        env = self._make_grid()
        env.reset()
        rendered = env.render()
        assert "#" in rendered
        assert "G" in rendered
        assert "X" in rendered
        assert "A" in rendered


# ── QTable ──


class TestQTable:
    def test_default_zero(self):
        """Unvisited state-action returns 0.0."""
        qt = QTable()
        assert qt.get((0, 0), Action.UP) == 0.0

    def test_set_and_get(self):
        """Set and retrieve Q-value."""
        qt = QTable()
        qt.set((0, 0), Action.UP, 5.0)
        assert qt.get((0, 0), Action.UP) == 5.0

    def test_best_action(self):
        """best_action returns action with highest Q-value."""
        qt = QTable()
        qt.set((0, 0), Action.UP, 1.0)
        qt.set((0, 0), Action.DOWN, 5.0)
        qt.set((0, 0), Action.LEFT, 2.0)
        qt.set((0, 0), Action.RIGHT, 3.0)
        assert qt.best_action((0, 0), list(Action)) == Action.DOWN

    def test_max_value(self):
        """max_value returns the maximum Q-value."""
        qt = QTable()
        qt.set((0, 0), Action.UP, 1.0)
        qt.set((0, 0), Action.DOWN, 5.0)
        assert qt.max_value((0, 0), list(Action)) == 5.0

    def test_max_value_empty(self):
        """max_value with no actions returns 0.0."""
        qt = QTable()
        assert qt.max_value((0, 0), []) == 0.0


# ── EpsilonGreedyPolicy ──


class TestEpsilonGreedyPolicy:
    def test_greedy(self):
        """With epsilon=0, always picks best action."""
        random.seed(42)
        qt = QTable()
        qt.set((0, 0), Action.RIGHT, 10.0)
        policy = EpsilonGreedyPolicy()
        for _ in range(10):
            a = policy.select(qt, (0, 0), list(Action), epsilon=0.0)
            assert a == Action.RIGHT

    def test_explores(self):
        """With epsilon=1, picks randomly."""
        random.seed(42)
        qt = QTable()
        qt.set((0, 0), Action.RIGHT, 10.0)
        policy = EpsilonGreedyPolicy()
        actions_seen = set()
        for _ in range(100):
            a = policy.select(qt, (0, 0), list(Action), epsilon=1.0)
            actions_seen.add(a)
        assert len(actions_seen) > 1  # Should explore multiple


# ── QLearningAgent ──


class TestQLearningAgent:
    def test_update_bellman(self):
        """Q-learning update follows Bellman equation."""
        agent = QLearningAgent(learning_rate=0.5, discount_factor=0.9, epsilon=0.0)
        state = (0, 0)
        action = Action.RIGHT
        next_state = (0, 1)
        next_actions = list(Action)
        # Q(s,a) starts at 0. reward=1, max_next_Q=0
        # new_Q = 0 + 0.5 * (1 + 0.9*0 - 0) = 0.5
        agent.update(state, action, 1.0, next_state, next_actions)
        assert agent.q_table.get(state, action) == pytest.approx(0.5)

    def test_update_with_existing_value(self):
        """Q-learning update with non-zero current value."""
        agent = QLearningAgent(learning_rate=0.5, discount_factor=0.9, epsilon=0.0)
        agent.q_table.set((0, 0), Action.RIGHT, 2.0)
        agent.q_table.set((0, 1), Action.RIGHT, 3.0)
        # Q(s,a) = 2. reward=1, max_next_Q=3
        # new_Q = 2 + 0.5 * (1 + 0.9*3 - 2) = 2 + 0.5 * 1.7 = 2.85
        agent.update((0, 0), Action.RIGHT, 1.0, (0, 1), list(Action))
        assert agent.q_table.get((0, 0), Action.RIGHT) == pytest.approx(2.85)

    def test_train_episode_returns_reward(self):
        """Training an episode returns total reward."""
        random.seed(42)
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        agent = QLearningAgent(learning_rate=0.1, discount_factor=0.99, epsilon=0.5)
        reward = agent.train_episode(env, max_steps=50)
        assert isinstance(reward, float)

    def test_training_convergence(self):
        """Q-learning converges to positive total reward on simple grid."""
        random.seed(42)
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        agent = QLearningAgent(learning_rate=0.2, discount_factor=0.95, epsilon=0.3)
        rewards = []
        for _ in range(200):
            r = agent.train_episode(env, max_steps=50)
            rewards.append(r)
        # Later episodes should earn more reward on average
        early_avg = sum(rewards[:50]) / 50
        late_avg = sum(rewards[-50:]) / 50
        assert late_avg > early_avg


# ── SARSAAgent ──


class TestSARSAAgent:
    def test_sarsa_update(self):
        """SARSA update uses actual next action, not max."""
        agent = SARSAAgent(learning_rate=0.5, discount_factor=0.9, epsilon=0.0)
        state = (0, 0)
        action = Action.RIGHT
        next_state = (0, 1)
        next_action = Action.UP
        # Q(next_state, UP) = 0
        # new_Q = 0 + 0.5 * (1 + 0.9*0 - 0) = 0.5
        agent.update(state, action, 1.0, next_state, next_action)
        assert agent.q_table.get(state, action) == pytest.approx(0.5)

    def test_sarsa_differs_from_qlearning(self):
        """SARSA and Q-learning produce different Q-values."""
        q_agent = QLearningAgent(learning_rate=0.5, discount_factor=0.9, epsilon=0.0)
        s_agent = SARSAAgent(learning_rate=0.5, discount_factor=0.9, epsilon=0.0)

        state = (0, 0)
        next_state = (0, 1)

        # Set different Q values for next state actions
        q_agent.q_table.set(next_state, Action.UP, 10.0)
        q_agent.q_table.set(next_state, Action.DOWN, 1.0)
        s_agent.q_table.set(next_state, Action.UP, 10.0)
        s_agent.q_table.set(next_state, Action.DOWN, 1.0)

        # Q-learning uses max (UP, Q=10), SARSA uses actual next action (DOWN, Q=1)
        q_agent.update(state, Action.RIGHT, 1.0, next_state, list(Action))
        s_agent.update(state, Action.RIGHT, 1.0, next_state, Action.DOWN)

        q_val = q_agent.q_table.get(state, Action.RIGHT)
        s_val = s_agent.q_table.get(state, Action.RIGHT)
        assert q_val != s_val  # Q-learning uses max, SARSA uses actual

    def test_sarsa_train_episode(self):
        """SARSA training returns a float reward."""
        random.seed(42)
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        agent = SARSAAgent(learning_rate=0.1, discount_factor=0.99, epsilon=0.5)
        reward = agent.train_episode(env, max_steps=50)
        assert isinstance(reward, float)


# ── ExperienceReplay ──


class TestExperienceReplay:
    def test_add_and_size(self):
        """Buffer tracks size correctly."""
        er = ExperienceReplay(buffer_size=100)
        er.add((0, 0), Action.UP, 1.0, (0, 0), False)
        assert er.size() == 1

    def test_buffer_limit(self):
        """Buffer respects max size."""
        er = ExperienceReplay(buffer_size=5)
        for i in range(10):
            er.add((i, 0), Action.UP, 1.0, (i + 1, 0), False)
        assert er.size() == 5

    def test_sample(self):
        """Sample returns correct batch size."""
        er = ExperienceReplay(buffer_size=100)
        for i in range(20):
            er.add((i, 0), Action.UP, 1.0, (i + 1, 0), False)
        batch = er.sample(5)
        assert len(batch) == 5

    def test_sample_larger_than_buffer(self):
        """Sample handles batch_size > buffer size."""
        er = ExperienceReplay(buffer_size=100)
        er.add((0, 0), Action.UP, 1.0, (1, 0), False)
        er.add((1, 0), Action.DOWN, 0.0, (2, 0), True)
        batch = er.sample(10)
        assert len(batch) == 2  # Only 2 items available

    def test_sample_returns_tuples(self):
        """Sampled items are (state, action, reward, next_state, done)."""
        er = ExperienceReplay(buffer_size=100)
        er.add((0, 0), Action.UP, 1.0, (0, 0), False)
        batch = er.sample(1)
        assert len(batch[0]) == 5


# ── Agent ──


class TestAgent:
    def test_agent_creation(self):
        """Agent stores id and creates Q-table."""
        agent = Agent("driver_1")
        assert agent.id == "driver_1"
        assert isinstance(agent.q_table, QTable)

    def test_agent_select_action(self):
        """Agent selects valid actions."""
        random.seed(42)
        agent = Agent("driver_1", epsilon=0.0)
        agent.q_table.set((0, 0), Action.RIGHT, 5.0)
        action = agent.select_action((0, 0), list(Action))
        assert action == Action.RIGHT


# ── SharedQTable ──


class TestSharedQTable:
    def test_thread_safe_get_set(self):
        """SharedQTable supports get and set."""
        sq = SharedQTable()
        sq.set((0, 0), Action.UP, 3.0)
        assert sq.get((0, 0), Action.UP) == 3.0

    def test_best_action(self):
        """SharedQTable returns best action."""
        sq = SharedQTable()
        sq.set((0, 0), Action.UP, 1.0)
        sq.set((0, 0), Action.DOWN, 5.0)
        assert sq.best_action((0, 0), list(Action)) == Action.DOWN

    def test_max_value(self):
        """SharedQTable returns max value."""
        sq = SharedQTable()
        sq.set((0, 0), Action.LEFT, 7.0)
        assert sq.max_value((0, 0), list(Action)) == 7.0


# ── IndependentQLearning ──


class TestIndependentQLearning:
    def test_independent_step(self):
        """Each agent's Q-table is updated independently."""
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        agents = [Agent("a1"), Agent("a2")]
        iql = IndependentQLearning(agents, env, learning_rate=0.5, discount_factor=0.9)

        iql.step("a1", (0, 0), Action.RIGHT, 1.0, (0, 1), list(Action))
        # Only a1's Q-table should be updated
        assert agents[0].q_table.get((0, 0), Action.RIGHT) == pytest.approx(0.5)
        assert agents[1].q_table.get((0, 0), Action.RIGHT) == 0.0

    def test_select_actions(self):
        """All agents select actions independently."""
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        agents = [Agent("a1"), Agent("a2")]
        iql = IndependentQLearning(agents, env)

        states = {"a1": (0, 0), "a2": (1, 1)}
        actions = iql.select_actions(states)
        assert "a1" in actions
        assert "a2" in actions


# ── CommunicationChannel ──


class TestCommunicationChannel:
    def test_send_receive(self):
        """Messages are received after sending."""
        ch = CommunicationChannel()
        ch.register("a1")
        ch.register("a2")
        ch.send("a1", {"reward": 5.0})
        msgs = ch.receive("a2")
        assert len(msgs) == 1
        assert msgs[0]["reward"] == 5.0
        assert msgs[0]["sender"] == "a1"

    def test_receive_clears_inbox(self):
        """Receiving clears the agent's inbox."""
        ch = CommunicationChannel()
        ch.register("a1")
        ch.send("a1", {"reward": 1.0})
        ch.receive("a1")
        assert ch.receive("a1") == []

    def test_clear_all(self):
        """Clear removes all messages."""
        ch = CommunicationChannel()
        ch.register("a1")
        ch.send("a1", {"reward": 1.0})
        ch.clear()
        assert ch.receive("a1") == []

    def test_unregistered_receive(self):
        """Unregistered agent receives empty list."""
        ch = CommunicationChannel()
        assert ch.receive("unknown") == []


# ── CoordinatedAgents ──


class TestCoordinatedAgents:
    def test_joint_reward(self):
        """Joint reward is mean of individual rewards."""
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        ch = CommunicationChannel()
        agents = [Agent("a1"), Agent("a2")]
        ca = CoordinatedAgents(agents, env, ch)

        joint = ca.get_joint_reward({"a1": 4.0, "a2": 6.0})
        assert joint == pytest.approx(5.0)

    def test_coordinate_step_updates(self):
        """Coordinated step updates Q-tables with joint reward."""
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        ch = CommunicationChannel()
        agents = [Agent("a1"), Agent("a2")]
        ca = CoordinatedAgents(agents, env, ch, learning_rate=1.0, discount_factor=0.0)

        states = {
            "a1": ((0, 0), Action.RIGHT, (0, 1), list(Action)),
            "a2": ((1, 0), Action.DOWN, (2, 0), list(Action)),
        }
        rewards = {"a1": 4.0, "a2": 6.0}
        ca.coordinate_step(states, rewards)

        # Joint reward = 5.0, lr=1.0, gamma=0
        # Q = 0 + 1.0 * (5.0 + 0 - 0) = 5.0
        assert agents[0].q_table.get((0, 0), Action.RIGHT) == pytest.approx(5.0)
        assert agents[1].q_table.get((1, 0), Action.DOWN) == pytest.approx(5.0)

    def test_joint_reward_empty(self):
        """Empty rewards give 0 joint reward."""
        env = GridWorld(rows=3, cols=3, goals={(2, 2): 10.0})
        ch = CommunicationChannel()
        agents = [Agent("a1")]
        ca = CoordinatedAgents(agents, env, ch)
        assert ca.get_joint_reward({}) == 0.0
