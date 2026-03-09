"""
Hyperparameter Tuning
======================

Model performance depends heavily on hyperparameters -- settings you choose
BEFORE training starts (learning rate, number of layers, regularization
strength). Finding good hyperparameters is called "tuning."

Three strategies, from simplest to most sophisticated:

**Grid Search**: Try every combination. Simple but exponentially expensive.
  10 values x 10 values x 10 values = 1000 combinations to try.

**Random Search**: Randomly sample combinations. Often finds good results
  faster than grid search because it explores more of each dimension.
  (A grid of 100 points in 2D covers 10 values per dimension. 100 random
  points covers 100 unique values per dimension.)

**Bayesian Optimization (TPE)**: Uses past results to suggest smarter next
  trials. Splits previous trials into "good" and "bad" groups, then suggests
  parameters that are more likely under the "good" distribution.
  This converges to optimal parameters faster than random search.

All three produce candidate parameter dicts that you then evaluate
(typically with cross-validation).
"""

from __future__ import annotations

import math
import random
from itertools import product


class ParameterSpace:
    """Defines the hyperparameter search space.

    Supports three types of parameters:
    - Integer: discrete values in [low, high] (e.g., n_layers in [1, 10])
    - Float: continuous values in [low, high] (e.g., learning_rate in [0.0001, 0.1])
    - Categorical: a set of discrete choices (e.g., optimizer in ['sgd', 'adam'])

    Float parameters can use log_scale=True when the range spans orders
    of magnitude (e.g., learning rate from 0.0001 to 0.1). Log scale
    samples uniformly in log space, giving equal probability to each
    order of magnitude.
    """

    def __init__(self) -> None:
        self._params: dict[str, dict] = {}

    def add_int(self, name: str, low: int, high: int) -> None:
        """Add an integer parameter.

        Args:
            name: Parameter name.
            low: Minimum value (inclusive).
            high: Maximum value (inclusive).
        """
        if low > high:
            raise ValueError(f"low ({low}) must be <= high ({high})")
        self._params[name] = {"type": "int", "low": low, "high": high}

    def add_float(
        self, name: str, low: float, high: float, log_scale: bool = False
    ) -> None:
        """Add a float parameter.

        Args:
            name: Parameter name.
            low: Minimum value.
            high: Maximum value.
            log_scale: If True, sample uniformly in log space.
        """
        if low > high:
            raise ValueError(f"low ({low}) must be <= high ({high})")
        if log_scale and low <= 0:
            raise ValueError("log_scale requires low > 0")
        self._params[name] = {
            "type": "float",
            "low": low,
            "high": high,
            "log_scale": log_scale,
        }

    def add_categorical(self, name: str, choices: list) -> None:
        """Add a categorical parameter.

        Args:
            name: Parameter name.
            choices: List of possible values.
        """
        if not choices:
            raise ValueError("choices must not be empty")
        self._params[name] = {"type": "categorical", "choices": list(choices)}

    @property
    def params(self) -> dict[str, dict]:
        """Return the parameter definitions."""
        return dict(self._params)


class GridSearch:
    """Exhaustive search over all parameter combinations.

    For each parameter, generates a set of values, then produces every
    possible combination. This guarantees finding the best combination
    within the grid, but is exponentially expensive.

    For integer params: all values in [low, high].
    For float params: 5 evenly spaced values in [low, high].
    For categorical params: all choices.
    """

    def __init__(self, param_space: ParameterSpace) -> None:
        self.param_space = param_space

    def generate_candidates(self) -> list[dict]:
        """Generate all parameter combinations.

        Returns:
            List of parameter dicts, one per combination.
        """
        param_values: dict[str, list] = {}

        for name, config in self.param_space.params.items():
            if config["type"] == "int":
                param_values[name] = list(range(config["low"], config["high"] + 1))
            elif config["type"] == "float":
                low, high = config["low"], config["high"]
                if config.get("log_scale"):
                    log_low = math.log(low)
                    log_high = math.log(high)
                    param_values[name] = [
                        math.exp(log_low + i * (log_high - log_low) / 4)
                        for i in range(5)
                    ]
                else:
                    step = (high - low) / 4 if high != low else 0
                    param_values[name] = [low + i * step for i in range(5)]
            elif config["type"] == "categorical":
                param_values[name] = config["choices"]

        # Cartesian product of all parameter values
        names = list(param_values.keys())
        value_lists = [param_values[n] for n in names]

        candidates = []
        for combo in product(*value_lists):
            candidates.append(dict(zip(names, combo)))

        return candidates


class RandomSearch:
    """Random sampling from parameter space.

    Draws n_trials random combinations. Often more efficient than grid
    search because:
    - Each trial explores a unique value per dimension
    - Unimportant dimensions don't waste budget
    - Easy to add more trials incrementally
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        n_trials: int = 10,
        seed: int = 42,
    ) -> None:
        if n_trials < 1:
            raise ValueError("n_trials must be >= 1")
        self.param_space = param_space
        self.n_trials = n_trials
        self.seed = seed

    def generate_candidates(self) -> list[dict]:
        """Generate random parameter combinations.

        Returns:
            List of n_trials parameter dicts.
        """
        rng = random.Random(self.seed)
        candidates = []

        for _ in range(self.n_trials):
            params = {}
            for name, config in self.param_space.params.items():
                if config["type"] == "int":
                    params[name] = rng.randint(config["low"], config["high"])
                elif config["type"] == "float":
                    if config.get("log_scale"):
                        log_low = math.log(config["low"])
                        log_high = math.log(config["high"])
                        params[name] = math.exp(rng.uniform(log_low, log_high))
                    else:
                        params[name] = rng.uniform(config["low"], config["high"])
                elif config["type"] == "categorical":
                    params[name] = rng.choice(config["choices"])

            candidates.append(params)

        return candidates


class BayesianOptimizer:
    """Simplified Tree-structured Parzen Estimator (TPE).

    The idea behind TPE:
    1. Run some initial random trials to build a baseline.
    2. Split all completed trials into "good" (top percentile) and "bad".
    3. For each parameter, estimate a distribution from the "good" group.
    4. Suggest new parameters by sampling from the "good" distributions.

    This is a simplified version that:
    - Uses the mean/std of good trials for float/int params.
    - Uses the most common value among good trials for categorical params.
    - Falls back to random sampling when not enough trials exist.
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        n_initial: int = 5,
        seed: int = 42,
    ) -> None:
        """Initialize the Bayesian optimizer.

        Args:
            param_space: The parameter search space.
            n_initial: Number of random trials before switching to TPE.
            seed: Random seed for reproducibility.
        """
        self.param_space = param_space
        self.n_initial = n_initial
        self.seed = seed
        self._rng = random.Random(seed)

    def suggest(self, trials: list[dict]) -> dict:
        """Suggest the next set of parameters to try.

        Args:
            trials: List of previous trials, each a dict with:
                    - 'params': dict of parameter values
                    - 'score': metric value (lower is better)

        Returns:
            A dict of suggested parameter values.
        """
        # Not enough data yet -- use random sampling
        if len(trials) < self.n_initial:
            return self._random_sample()

        # Split into good/bad trials
        good_trials, bad_trials = self._split_trials(trials)

        # Build suggestion from good trial distributions
        suggestion = {}
        for name, config in self.param_space.params.items():
            good_values = [t["params"][name] for t in good_trials]

            if config["type"] in ("int", "float"):
                # Use mean/std of good values, clamped to bounds
                if len(good_values) >= 2:
                    mean = sum(good_values) / len(good_values)
                    std = (
                        sum((v - mean) ** 2 for v in good_values)
                        / (len(good_values) - 1)
                    ) ** 0.5
                    # Sample from normal distribution around good mean
                    value = self._rng.gauss(mean, max(std, 1e-6))
                else:
                    value = good_values[0]

                # Clamp to bounds
                value = max(config["low"], min(config["high"], value))
                if config["type"] == "int":
                    value = round(value)
                suggestion[name] = value

            elif config["type"] == "categorical":
                # Use most common value among good trials
                counts: dict = {}
                for v in good_values:
                    counts[v] = counts.get(v, 0) + 1
                # With some exploration probability, pick randomly
                if self._rng.random() < 0.2:
                    suggestion[name] = self._rng.choice(config["choices"])
                else:
                    suggestion[name] = max(counts, key=counts.get)

        return suggestion

    def _split_trials(
        self,
        trials: list[dict],
        percentile: float = 0.25,
    ) -> tuple[list[dict], list[dict]]:
        """Split trials into good (low score) and bad (high score) groups.

        Args:
            trials: All completed trials with 'score' keys.
            percentile: Fraction of trials to consider "good" (top 25%).

        Returns:
            (good_trials, bad_trials) tuple.
        """
        sorted_trials = sorted(trials, key=lambda t: t["score"])
        n_good = max(1, int(len(sorted_trials) * percentile))
        return sorted_trials[:n_good], sorted_trials[n_good:]

    def _random_sample(self) -> dict:
        """Generate a random parameter combination (used for initial trials)."""
        params = {}
        for name, config in self.param_space.params.items():
            if config["type"] == "int":
                params[name] = self._rng.randint(config["low"], config["high"])
            elif config["type"] == "float":
                if config.get("log_scale"):
                    log_low = math.log(config["low"])
                    log_high = math.log(config["high"])
                    params[name] = math.exp(self._rng.uniform(log_low, log_high))
                else:
                    params[name] = self._rng.uniform(config["low"], config["high"])
            elif config["type"] == "categorical":
                params[name] = self._rng.choice(config["choices"])
        return params
