"""
M36: Reinforcement Learning for Dispatch — MDPs, Q-learning, multi-agent RL.

This module formalizes ride-sharing dispatch as a reinforcement learning
problem: GridWorld environments for learning RL concepts, Q-learning and
SARSA for policy optimization, and multi-agent coordination for fleet
management.
"""

from .mdp_environment import State, Action, Transition, MDP, GridWorld
from .q_learning import QTable, EpsilonGreedyPolicy, QLearningAgent, SARSAAgent, ExperienceReplay
from .multi_agent import Agent, SharedQTable, IndependentQLearning, CommunicationChannel, CoordinatedAgents
