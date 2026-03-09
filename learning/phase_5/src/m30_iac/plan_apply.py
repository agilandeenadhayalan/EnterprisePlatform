"""
Plan / Apply — Terraform-style plan and apply workflow.

WHY THIS MATTERS:
The plan/apply workflow is the core of infrastructure-as-code safety:
  1. Plan: compute a diff between desired state (config) and current
     state (state file). Show what will be created, updated, or deleted.
  2. Review: the engineer reviews the plan before any changes are made.
  3. Apply: execute the plan, updating real infrastructure and the
     state file simultaneously.

This two-phase approach prevents surprises: you always know what
Terraform will do before it does it.

Key concepts:
  - CREATE: resource exists in config but not in state (new resource).
  - UPDATE: resource exists in both but properties differ (changed).
  - DELETE: resource exists in state but not in config (removed).
  - NO_OP: resource exists in both with identical properties (unchanged).
  - Dependency-ordered apply: resources are applied in topological
    order to respect dependencies.
"""

from enum import Enum

from .state_management import StateStore


class ActionType(Enum):
    """The type of infrastructure change to make.

    CREATE — provision a new resource.
    UPDATE — modify an existing resource in place.
    DELETE — destroy and remove a resource.
    NO_OP  — no change needed (desired == actual).
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no_op"


class Action:
    """A single planned infrastructure change.

    Each action describes:
    - resource_id: which resource to change.
    - action_type: create, update, delete, or no_op.
    - old_properties: current state (None for CREATE).
    - new_properties: desired state (None for DELETE).
    - reason: human-readable explanation of why this action is needed.
    """

    def __init__(
        self,
        resource_id: str,
        action_type: ActionType,
        old_properties: dict = None,
        new_properties: dict = None,
        reason: str = "",
    ):
        self.resource_id = resource_id
        self.action_type = action_type
        self.old_properties = old_properties
        self.new_properties = new_properties
        self.reason = reason


class Plan:
    """A Terraform execution plan — the set of actions to perform.

    The plan is computed by comparing desired state (from config) with
    current state (from the state store). It provides a summary of
    changes and can be filtered by action type.

    Engineers review the plan output before typing `terraform apply`.
    """

    def __init__(self, actions: list = None):
        self.actions = actions or []

    def summary(self) -> dict:
        """Summarize the plan as a count of each action type.

        Returns:
            A dict like {create: 2, update: 1, delete: 0, no_op: 5}.
        """
        counts = {
            "create": 0,
            "update": 0,
            "delete": 0,
            "no_op": 0,
        }
        for action in self.actions:
            counts[action.action_type.value] += 1
        return counts

    def has_changes(self) -> bool:
        """Check if the plan contains any real changes.

        Returns True if there are any CREATE, UPDATE, or DELETE actions.
        Returns False if all actions are NO_OP.
        """
        return any(
            action.action_type != ActionType.NO_OP
            for action in self.actions
        )

    def get_actions(self, action_type: ActionType = None) -> list:
        """Get actions, optionally filtered by type.

        Args:
            action_type: if provided, only return actions of this type.
                         if None, return all actions.
        """
        if action_type is None:
            return list(self.actions)
        return [a for a in self.actions if a.action_type == action_type]


class PlanEngine:
    """Computes a plan by diffing desired state against current state.

    This is the core of `terraform plan`. For each resource:
    - In desired but not current → CREATE
    - In both but properties differ → UPDATE
    - In current but not desired → DELETE
    - In both with same properties → NO_OP
    """

    def plan(self, desired: dict, current: StateStore) -> Plan:
        """Compute a plan from desired config and current state.

        Args:
            desired: dict of resource_id -> properties (from config).
            current: StateStore with current infrastructure state.

        Returns:
            A Plan containing the actions needed to reach desired state.
        """
        actions = []

        # Resources in desired: CREATE or UPDATE
        for rid, props in desired.items():
            state = current.get(rid)
            if state is None:
                actions.append(Action(
                    resource_id=rid,
                    action_type=ActionType.CREATE,
                    old_properties=None,
                    new_properties=props,
                    reason="resource does not exist in current state",
                ))
            elif state.properties != props:
                actions.append(Action(
                    resource_id=rid,
                    action_type=ActionType.UPDATE,
                    old_properties=state.properties,
                    new_properties=props,
                    reason="resource properties have changed",
                ))
            else:
                actions.append(Action(
                    resource_id=rid,
                    action_type=ActionType.NO_OP,
                    old_properties=state.properties,
                    new_properties=props,
                    reason="no changes",
                ))

        # Resources in current but not desired → DELETE
        for state in current.list_all():
            if state.resource_id not in desired:
                actions.append(Action(
                    resource_id=state.resource_id,
                    action_type=ActionType.DELETE,
                    old_properties=state.properties,
                    new_properties=None,
                    reason="resource not in desired configuration",
                ))

        return Plan(actions)


class ApplyResult:
    """The result of applying a plan.

    Tracks which actions succeeded, which failed, and the final
    state of the state store after the apply.
    """

    def __init__(self, succeeded: list = None, failed: list = None, state: StateStore = None):
        self.succeeded = succeeded or []
        self.failed = failed or []
        self.state = state


class ApplyEngine:
    """Executes a plan against the state store.

    In real Terraform, this would make API calls to cloud providers.
    Here we simulate the apply by updating the state store directly.

    Actions are executed in dependency_order if provided. Each action
    updates the state store as it completes, ensuring the state file
    is always consistent even if the apply is interrupted.
    """

    def apply(self, plan: Plan, state: StateStore, dependency_order: list = None) -> ApplyResult:
        """Execute a plan and update the state store.

        Args:
            plan: the Plan to execute.
            state: the StateStore to update.
            dependency_order: optional list of resource_ids specifying
                              the order to apply actions. If None,
                              actions are applied in plan order.

        Returns:
            An ApplyResult with succeeded/failed actions and final state.
        """
        succeeded = []
        failed = []

        # Build action lookup for ordering
        action_map = {a.resource_id: a for a in plan.actions}

        if dependency_order:
            # Apply in dependency order, then any remaining actions
            ordered_ids = list(dependency_order)
            for action in plan.actions:
                if action.resource_id not in ordered_ids:
                    ordered_ids.append(action.resource_id)
            ordered_actions = [
                action_map[rid] for rid in ordered_ids
                if rid in action_map
            ]
        else:
            ordered_actions = plan.actions

        for action in ordered_actions:
            try:
                if action.action_type == ActionType.CREATE:
                    state.set(action.resource_id, action.new_properties, "created")
                elif action.action_type == ActionType.UPDATE:
                    state.set(action.resource_id, action.new_properties, "updated")
                elif action.action_type == ActionType.DELETE:
                    state.delete(action.resource_id)
                # NO_OP: do nothing
                succeeded.append(action)
            except Exception:
                failed.append(action)

        return ApplyResult(succeeded=succeeded, failed=failed, state=state)
