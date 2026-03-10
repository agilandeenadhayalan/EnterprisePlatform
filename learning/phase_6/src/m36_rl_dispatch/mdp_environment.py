"""
MDP Environments — Markov Decision Process formalization and GridWorld.

WHY THIS MATTERS:
Ride-sharing dispatch is fundamentally a sequential decision problem:
at each time step, the platform decides which driver to assign to which
rider, balancing immediate rewards (short pickup time) against future
consequences (driver availability for next requests). MDPs formalize
this as states, actions, transitions, and rewards.

Key concepts:
  - State: current situation (driver locations, pending requests).
  - Action: decision to take (assign driver X to request Y, reposition
    to zone Z).
  - Transition: probability of reaching next state given current state
    and action. Captures uncertainty (traffic, cancellations).
  - Reward: immediate payoff (fare earned, wait time penalty).
  - GridWorld: simplified spatial environment for learning RL concepts
    before tackling real dispatch.
"""

from dataclasses import dataclass, field
from enum import Enum


class Action(Enum):
    """Possible actions in a GridWorld environment."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class State:
    """A state in the MDP.

    Attributes:
        id: unique state identifier
        name: human-readable name
        is_terminal: whether this is a terminal (absorbing) state
        reward: reward received upon entering this state
    """
    id: str
    name: str
    is_terminal: bool = False
    reward: float = 0.0


@dataclass
class Transition:
    """A transition in the MDP.

    Represents P(next_state | state, action) with associated reward.

    Attributes:
        state_id: source state
        action: action taken
        next_state_id: destination state
        probability: transition probability (0-1)
        reward: reward for this transition
    """
    state_id: str
    action: Action
    next_state_id: str
    probability: float
    reward: float


class MDP:
    """Markov Decision Process.

    A formal framework for sequential decision-making under uncertainty.
    Defined by (S, A, P, R) where S is states, A is actions, P is
    transition probabilities, R is rewards.
    """

    def __init__(self):
        self._states: dict[str, State] = {}
        self._transitions: dict[str, dict[Action, list[Transition]]] = {}

    def add_state(self, state: State) -> None:
        """Add a state to the MDP."""
        self._states[state.id] = state
        if state.id not in self._transitions:
            self._transitions[state.id] = {}

    def add_transition(self, transition: Transition) -> None:
        """Add a transition to the MDP."""
        if transition.state_id not in self._transitions:
            self._transitions[transition.state_id] = {}
        if transition.action not in self._transitions[transition.state_id]:
            self._transitions[transition.state_id][transition.action] = []
        self._transitions[transition.state_id][transition.action].append(transition)

    def get_transitions(self, state_id: str, action: Action) -> list[Transition]:
        """Get all possible transitions for a state-action pair."""
        if state_id not in self._transitions:
            return []
        return self._transitions[state_id].get(action, [])

    def get_actions(self, state_id: str) -> list[Action]:
        """Get available actions for a state."""
        if state_id not in self._transitions:
            return []
        return list(self._transitions[state_id].keys())

    def is_terminal(self, state_id: str) -> bool:
        """Check if a state is terminal."""
        if state_id in self._states:
            return self._states[state_id].is_terminal
        return False


class GridWorld:
    """A grid-based environment for reinforcement learning.

    The agent starts at (0, 0) and navigates a grid with walls, goals
    (positive rewards), and traps (negative rewards). Movement is
    deterministic: the agent moves one cell in the chosen direction,
    clipped to grid bounds. Walls block movement.

    This is the standard RL testbed for learning value iteration,
    policy iteration, Q-learning, and SARSA before scaling to real
    dispatch problems.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        walls: list[tuple] = None,
        goals: dict[tuple, float] = None,
        traps: dict[tuple, float] = None,
    ):
        """Initialize GridWorld.

        Args:
            rows: number of rows
            cols: number of columns
            walls: list of (row, col) positions that block movement
            goals: dict mapping (row, col) to positive reward (terminal)
            traps: dict mapping (row, col) to negative reward (terminal)
        """
        self.rows = rows
        self.cols = cols
        self.walls = set(walls or [])
        self.goals = goals or {}
        self.traps = traps or {}
        self._agent_pos: tuple = (0, 0)

    def reset(self) -> tuple:
        """Reset the environment. Returns the start position (0, 0)."""
        self._agent_pos = (0, 0)
        return self._agent_pos

    def step(self, state: tuple, action: Action) -> tuple:
        """Take an action from the given state.

        Args:
            state: current (row, col) position
            action: direction to move

        Returns:
            (next_state, reward, done) tuple
        """
        row, col = state

        # Compute intended next position
        if action == Action.UP:
            new_row, new_col = row - 1, col
        elif action == Action.DOWN:
            new_row, new_col = row + 1, col
        elif action == Action.LEFT:
            new_row, new_col = row, col - 1
        elif action == Action.RIGHT:
            new_row, new_col = row, col + 1
        else:
            new_row, new_col = row, col

        # Clip to grid bounds
        new_row = max(0, min(self.rows - 1, new_row))
        new_col = max(0, min(self.cols - 1, new_col))

        # Walls block movement — stay in current position
        if (new_row, new_col) in self.walls:
            new_row, new_col = row, col

        next_state = (new_row, new_col)

        # Check goals and traps
        if next_state in self.goals:
            return (next_state, self.goals[next_state], True)
        elif next_state in self.traps:
            return (next_state, self.traps[next_state], True)
        else:
            return (next_state, -0.1, False)  # Small step penalty

    def get_valid_actions(self, state: tuple) -> list[Action]:
        """Get all valid actions from a state.

        All four directions are always valid (movement is clipped to
        bounds and walls block rather than raise errors).
        """
        return list(Action)

    def render(self) -> str:
        """Render the grid as ASCII art.

        Legend: A=agent, #=wall, G=goal, X=trap, .=empty
        """
        lines = []
        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                pos = (r, c)
                if pos == self._agent_pos:
                    row_str += "A"
                elif pos in self.walls:
                    row_str += "#"
                elif pos in self.goals:
                    row_str += "G"
                elif pos in self.traps:
                    row_str += "X"
                else:
                    row_str += "."
            lines.append(row_str)
        return "\n".join(lines)
