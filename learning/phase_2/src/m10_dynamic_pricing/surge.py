"""
Surge Pricing Calculator
=========================

Implements multiple surge pricing models that convert a demand/supply
ratio into a price multiplier.

Models:
1. Linear:      multiplier = base + k * (ratio - threshold)
2. Exponential: multiplier = base * e^(k * (ratio - threshold))
3. Step:        multiplier jumps at predefined ratio breakpoints

WHY different models:
- Linear is predictable but may not respond fast enough to extreme surges
- Exponential reacts strongly to high demand but can produce scary prices
- Step function gives riders clear, predictable price tiers

All models clamp the multiplier to [1.0, max_multiplier] to prevent
runaway pricing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class SurgeModel(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"


@dataclass
class SurgeConfig:
    """Configuration for a surge pricing model."""
    model: SurgeModel = SurgeModel.LINEAR
    base_multiplier: float = 1.0
    max_multiplier: float = 5.0
    surge_threshold: float = 1.2    # Ratio above which surge kicks in
    linear_k: float = 1.0           # Slope for linear model
    exp_k: float = 0.5              # Growth rate for exponential model
    step_breakpoints: list[tuple[float, float]] | None = None
    # Default step breakpoints: (ratio_threshold, multiplier)

    def __post_init__(self) -> None:
        if self.step_breakpoints is None:
            self.step_breakpoints = [
                (1.2, 1.25),
                (1.5, 1.50),
                (2.0, 2.00),
                (2.5, 2.50),
                (3.0, 3.00),
                (4.0, 4.00),
            ]


def surge_multiplier_linear(
    ratio: float,
    config: SurgeConfig,
) -> float:
    """
    Linear surge: multiplier = base + k * (ratio - threshold).

    Grows linearly with excess demand. Predictable and easy to explain.
    """
    if ratio <= config.surge_threshold:
        return config.base_multiplier

    multiplier = config.base_multiplier + config.linear_k * (ratio - config.surge_threshold)
    return min(multiplier, config.max_multiplier)


def surge_multiplier_exponential(
    ratio: float,
    config: SurgeConfig,
) -> float:
    """
    Exponential surge: multiplier = base * e^(k * (ratio - threshold)).

    Reacts mildly to small imbalances but aggressively to large ones.
    """
    if ratio <= config.surge_threshold:
        return config.base_multiplier

    multiplier = config.base_multiplier * math.exp(
        config.exp_k * (ratio - config.surge_threshold)
    )
    return min(multiplier, config.max_multiplier)


def surge_multiplier_step(
    ratio: float,
    config: SurgeConfig,
) -> float:
    """
    Step function surge: multiplier jumps at predefined breakpoints.

    Riders see clear price tiers (1.25x, 1.5x, 2.0x, etc.) instead
    of confusing decimals like 1.347x.
    """
    assert config.step_breakpoints is not None
    multiplier = config.base_multiplier

    for threshold, step_mult in config.step_breakpoints:
        if ratio >= threshold:
            multiplier = step_mult

    return min(multiplier, config.max_multiplier)


def calculate_surge(
    demand: float,
    supply: float,
    config: SurgeConfig | None = None,
) -> float:
    """
    Calculate the surge multiplier given demand and supply.

    Returns a multiplier in [1.0, max_multiplier].

    # TODO: Experiment with your own surge formula here!
    # Ideas to try:
    #   - Add a time-decay factor (surge fades over minutes)
    #   - Add a rider-loyalty discount (frequent riders get lower surge)
    #   - Add supply-side incentive (show drivers the surge zone)
    #   - Implement a sigmoid curve (S-shape) for smooth transitions
    """
    if config is None:
        config = SurgeConfig()

    if supply <= 0:
        return config.max_multiplier

    ratio = demand / supply

    if config.model == SurgeModel.LINEAR:
        return surge_multiplier_linear(ratio, config)
    elif config.model == SurgeModel.EXPONENTIAL:
        return surge_multiplier_exponential(ratio, config)
    elif config.model == SurgeModel.STEP:
        return surge_multiplier_step(ratio, config)
    else:
        return config.base_multiplier


def calculate_fare(
    base_fare: float,
    distance_km: float,
    duration_minutes: float,
    surge: float = 1.0,
    per_km_rate: float = 1.50,
    per_min_rate: float = 0.30,
    minimum_fare: float = 5.00,
) -> float:
    """
    Calculate the total fare with surge pricing applied.

    fare = max(minimum, (base + distance_charge + time_charge) * surge)
    """
    distance_charge = distance_km * per_km_rate
    time_charge = duration_minutes * per_min_rate
    subtotal = (base_fare + distance_charge + time_charge) * surge
    return round(max(minimum_fare, subtotal), 2)
