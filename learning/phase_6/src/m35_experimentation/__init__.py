"""
M35: Experimentation — A/B testing, multi-armed bandits, and sequential analysis.

This module covers the statistical foundations of online experimentation:
from classical hypothesis testing (z-test, chi-square) to adaptive
algorithms (epsilon-greedy, UCB1, Thompson Sampling) and advanced
analysis techniques (sequential testing, multiple comparison corrections,
segment interactions).
"""

from .ab_testing import ExperimentDesign, SampleSizeCalculator, ZTest, ChiSquareTest, EffectSizeCalculator
from .multi_armed_bandit import BanditArm, EpsilonGreedy, UCB1, ThompsonSampling, RegretTracker
from .experiment_analysis import SequentialTest, MultipleComparisonCorrection, SegmentAnalyzer
