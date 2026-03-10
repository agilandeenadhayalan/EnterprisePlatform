"""
Exercise 5: Thompson Sampling with Beta Distribution
========================================
Implement a Thompson Sampling arm selection function using the Beta
distribution for Bernoulli bandits.

WHY THIS MATTERS:
Multi-armed bandits are everywhere in ride-sharing platforms:
  - Which pricing algorithm maximizes revenue? (explore vs exploit)
  - Which driver matching strategy minimizes wait time?
  - Which promotional offer converts best?

Thompson Sampling is the gold standard for online optimization:
  - It naturally balances exploration and exploitation
  - It has strong theoretical guarantees (Bayesian regret bounds)
  - It's simple to implement (~5 lines for the core logic)
  - It works with any likelihood model (Beta-Bernoulli is simplest)

The key insight: instead of computing confidence intervals (UCB) or
using a fixed exploration rate (epsilon-greedy), sample from the
posterior distribution of each arm's success probability. Arms you're
uncertain about will occasionally produce high samples, getting
explored. Arms you know are good will consistently produce high
samples, getting exploited.

YOUR TASK:
Implement select_arm(alphas, betas) that:
1. For each arm i, sample theta_i ~ Beta(alphas[i], betas[i])
2. Return the index of the arm with the highest theta_i

Use random.betavariate(alpha, beta) for sampling.
"""

import random


def select_arm(alphas: list[float], betas: list[float]) -> int:
    """Select an arm using Thompson Sampling.

    Args:
        alphas: list of alpha parameters (successes + 1) for each arm's
                Beta posterior. Higher alpha = more evidence of success.
        betas: list of beta parameters (failures + 1) for each arm's
               Beta posterior. Higher beta = more evidence of failure.

    Returns:
        Index of the arm with the highest sampled value.

    Algorithm:
        1. For each arm i, sample theta_i from Beta(alphas[i], betas[i])
        2. Return argmax(theta_i)
    """
    # YOUR CODE HERE (~5 lines)
    raise NotImplementedError("Implement select_arm")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    random.seed(42)

    # Test 1: Arm with much higher alpha should be selected most often
    alphas = [2.0, 50.0, 2.0]   # Arm 1 has strong evidence of success
    betas = [50.0, 2.0, 50.0]   # Arm 1 has little evidence of failure
    counts = [0, 0, 0]
    for _ in range(1000):
        arm = select_arm(alphas, betas)
        counts[arm] += 1
    assert counts[1] > counts[0] and counts[1] > counts[2], \
        f"Arm 1 should be selected most, got counts={counts}"
    print(f"[PASS] Strong arm selected most: {counts}")

    # Test 2: Equal priors lead to roughly equal selection
    alphas = [1.0, 1.0, 1.0]
    betas = [1.0, 1.0, 1.0]
    counts = [0, 0, 0]
    for _ in range(3000):
        arm = select_arm(alphas, betas)
        counts[arm] += 1
    for c in counts:
        assert 500 < c < 1500, f"Expected roughly equal, got {counts}"
    print(f"[PASS] Equal priors -> roughly equal: {counts}")

    # Test 3: Convergence simulation — best arm gets most pulls
    n_arms = 3
    true_probs = [0.1, 0.5, 0.9]  # Arm 2 is clearly best
    alphas = [1.0] * n_arms
    betas = [1.0] * n_arms
    pull_counts = [0] * n_arms

    for _ in range(500):
        arm = select_arm(alphas, betas)
        pull_counts[arm] += 1
        # Simulate reward
        reward = 1 if random.random() < true_probs[arm] else 0
        if reward:
            alphas[arm] += 1
        else:
            betas[arm] += 1

    assert pull_counts[2] > pull_counts[0], \
        f"Best arm (idx=2) should have most pulls, got {pull_counts}"
    print(f"[PASS] Convergence: pulls={pull_counts}, best arm dominated")

    # Test 4: Returns valid index
    arm = select_arm([1.0, 1.0], [1.0, 1.0])
    assert arm in [0, 1], f"Expected 0 or 1, got {arm}"
    print("[PASS] Returns valid index")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
