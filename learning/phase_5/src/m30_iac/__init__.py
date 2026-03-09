"""
M30: Infrastructure as Code — Resource graphs, state management, module
composition, and plan/apply workflows.

This module models the core Terraform/OpenTofu abstractions in pure Python
so you can understand how IaC tools manage infrastructure without needing
cloud provider accounts.
"""

from .resource_graph import Resource, ResourceGraph
from .state_management import ResourceState, StateStore, StateLock, DriftDetector, DriftResult
from .module_composition import Variable, Output, Module, ModuleComposer
from .plan_apply import ActionType, Action, Plan, PlanEngine, ApplyEngine, ApplyResult
