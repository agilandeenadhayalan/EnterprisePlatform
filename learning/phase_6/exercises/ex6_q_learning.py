"""
Exercise 6: Q-Learning for GridWorld
========================================
Implement Q-learning training for a GridWorld environment. The agent
learns to navigate from (0,0) to the goal by trial and error,
updating Q-values after each step using the Bellman equation.

WHY THIS MATTERS:
Q-learning is the foundation of reinforcement learning for dispatch:
  - A driver (agent) learns which zones to reposition to (actions)
    based on current location and demand (state) to maximize total
    fares (rewards) over a shift.
  - The Bellman equation lets the agent reason about long-term value:
    a zone with low immediate demand might be valuable because it's
    close to a high-demand zone that will be busy in 10 minutes.

Understanding Q-learning on a simple GridWorld builds intuition for:
  - The exploration-exploitation tradeoff (epsilon-greedy)
  - Temporal difference learning (bootstrapping from estimates)
  - Convergence properties (learning rate, discount factor)
  - The credit assignment problem (which action deserves credit?)

YOUR TASK:
Implement train(env, episodes, lr, gamma, epsilon) that:
1. Creates a Q-table (dict) mapping (state, action) -> value
2. For each episode:
   a. Reset the environment to get the start state
   b. Loop until done or max_steps reached:
      - Select action using epsilon-greedy (random.random() < epsilon -> random, else best)
      - Take action, observe (next_state, reward, done)
      - Update Q-value: Q(s,a) <- Q(s,a) + lr * (reward + gamma * max Q(s',a') - Q(s,a))
      - Move to next state
3. Return the Q-table

The Q-table should be a dict with keys (state_tuple, action_string).
"""

import random


def train(env, episodes: int = 500, lr: float = 0.1, gamma: float = 0.99, epsilon: float = 0.1) -> dict:
    """Train a Q-learning agent on a GridWorld environment.

    Args:
        env: GridWorld instance with methods:
             - reset() -> state (tuple)
             - step(state, action) -> (next_state, reward, done)
             - get_valid_actions(state) -> list[Action]
        episodes: number of training episodes
        lr: learning rate (alpha) for Q-value updates
        gamma: discount factor for future rewards
        epsilon: exploration rate for epsilon-greedy

    Returns:
        Q-table as a dict mapping (state, action_value) -> float.
        E.g., {((0,0), "right"): 2.5, ((0,1), "down"): 3.1, ...}

    Algorithm:
        For each episode:
            state = env.reset()
            while not done (max 100 steps):
                actions = env.get_valid_actions(state)
                if random.random() < epsilon:
                    action = random.choice(actions)
                else:
                    action = argmax_a Q(state, a)  # best action
                next_state, reward, done = env.step(state, action)
                # Bellman update:
                max_next_q = max(Q(next_state, a') for a' in valid_actions(next_state))
                Q(state, action) += lr * (reward + gamma * max_next_q - Q(state, action))
                state = next_state
    """
    # YOUR CODE HERE (~25 lines)
    raise NotImplementedError("Implement train")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    # Import GridWorld and Action here to avoid coupling the exercise
    # to the module structure — students can copy this file anywhere.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from m36_rl_dispatch.mdp_environment import GridWorld, Action

    random.seed(42)

    # Simple 4x4 grid: goal at (3,3), trap at (3,0)
    env = GridWorld(
        rows=4, cols=4,
        walls=[(1, 1), (2, 2)],
        goals={(3, 3): 10.0},
        traps={(3, 0): -10.0},
    )

    # Test 1: Training returns a dict
    q_table = train(env, episodes=500, lr=0.2, gamma=0.95, epsilon=0.3)
    assert isinstance(q_table, dict), f"Expected dict, got {type(q_table)}"
    assert len(q_table) > 0, "Q-table should not be empty"
    print(f"[PASS] Q-table has {len(q_table)} entries")

    # Test 2: Q-values near goal should be high
    # From (3,2), moving RIGHT reaches the goal
    goal_approach_key = ((3, 2), "right")
    if goal_approach_key in q_table:
        assert q_table[goal_approach_key] > 0, \
            f"Q-value approaching goal should be positive, got {q_table[goal_approach_key]}"
        print(f"[PASS] Q((3,2), right) = {q_table[goal_approach_key]:.2f} (positive)")
    else:
        print("[WARN] Q((3,2), right) not in table — may need more episodes")

    # Test 3: Q-values near trap should be negative
    trap_approach_key = ((2, 0), "down")
    if trap_approach_key in q_table:
        assert q_table[trap_approach_key] < 0, \
            f"Q-value approaching trap should be negative, got {q_table[trap_approach_key]}"
        print(f"[PASS] Q((2,0), down) = {q_table[trap_approach_key]:.2f} (negative)")
    else:
        print("[WARN] Q((2,0), down) not in table — may need more episodes")

    # Test 4: Trained agent can reach the goal
    state = env.reset()
    reached_goal = False
    for _ in range(50):
        actions = env.get_valid_actions(state)
        # Greedy: pick best action
        best_action = max(
            actions,
            key=lambda a: q_table.get((state, a.value), 0.0),
        )
        next_state, reward, done = env.step(state, best_action)
        if done and reward > 0:
            reached_goal = True
            break
        state = next_state
    assert reached_goal, "Trained agent should reach the goal"
    print("[PASS] Trained agent reaches the goal")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
