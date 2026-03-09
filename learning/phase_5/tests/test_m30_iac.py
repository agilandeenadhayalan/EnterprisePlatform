"""
Tests for M30: Infrastructure as Code — Resource graphs, state management,
module composition, and plan/apply workflows.
"""

import pytest

from m30_iac.resource_graph import Resource, ResourceGraph
from m30_iac.state_management import ResourceState, StateStore, StateLock, DriftDetector, DriftResult
from m30_iac.module_composition import Variable, Output, Module, ModuleComposer
from m30_iac.plan_apply import ActionType, Action, Plan, PlanEngine, ApplyEngine, ApplyResult


# ── ResourceGraph ──


class TestResourceGraph:
    def test_add_and_get(self):
        """Resources can be added and retrieved by ID."""
        g = ResourceGraph()
        r = Resource("aws_vpc", "main", {"cidr": "10.0.0.0/16"})
        g.add_resource(r)
        assert g.get_resource("aws_vpc.main").properties["cidr"] == "10.0.0.0/16"

    def test_get_missing_raises(self):
        """Getting a nonexistent resource raises KeyError."""
        g = ResourceGraph()
        with pytest.raises(KeyError, match="not found"):
            g.get_resource("aws_vpc.missing")

    def test_dependency_order_simple(self):
        """Topological sort puts dependencies before dependents."""
        g = ResourceGraph()
        vpc = Resource("aws_vpc", "main", {})
        subnet = Resource("aws_subnet", "main", {}, depends_on=["aws_vpc.main"])
        instance = Resource("aws_instance", "web", {}, depends_on=["aws_subnet.main"])
        # Add in reverse order to test sorting
        g.add_resource(instance)
        g.add_resource(subnet)
        g.add_resource(vpc)
        order = g.get_dependency_order()
        assert order.index("aws_vpc.main") < order.index("aws_subnet.main")
        assert order.index("aws_subnet.main") < order.index("aws_instance.web")

    def test_dependency_order_parallel(self):
        """Independent resources can appear in any order."""
        g = ResourceGraph()
        g.add_resource(Resource("aws_vpc", "a", {}))
        g.add_resource(Resource("aws_vpc", "b", {}))
        order = g.get_dependency_order()
        assert len(order) == 2
        assert set(order) == {"aws_vpc.a", "aws_vpc.b"}

    def test_cycle_detection(self):
        """Cycles in the dependency graph are detected."""
        g = ResourceGraph()
        a = Resource("res", "a", {}, depends_on=["res.b"])
        b = Resource("res", "b", {}, depends_on=["res.a"])
        g.add_resource(a)
        g.add_resource(b)
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_no_cycles(self):
        """Acyclic graph has no cycles."""
        g = ResourceGraph()
        g.add_resource(Resource("res", "a", {}))
        g.add_resource(Resource("res", "b", {}, depends_on=["res.a"]))
        assert g.detect_cycles() == []

    def test_dependents(self):
        """Find resources that directly depend on a given resource."""
        g = ResourceGraph()
        g.add_resource(Resource("aws_vpc", "main", {}))
        g.add_resource(Resource("aws_subnet", "a", {}, depends_on=["aws_vpc.main"]))
        g.add_resource(Resource("aws_subnet", "b", {}, depends_on=["aws_vpc.main"]))
        g.add_resource(Resource("aws_instance", "web", {}, depends_on=["aws_subnet.a"]))
        deps = g.get_dependents("aws_vpc.main")
        dep_ids = [d.resource_id for d in deps]
        assert "aws_subnet.a" in dep_ids
        assert "aws_subnet.b" in dep_ids
        assert "aws_instance.web" not in dep_ids

    def test_affected_resources(self):
        """Transitively affected resources are found via BFS."""
        g = ResourceGraph()
        g.add_resource(Resource("aws_vpc", "main", {}))
        g.add_resource(Resource("aws_subnet", "main", {}, depends_on=["aws_vpc.main"]))
        g.add_resource(Resource("aws_instance", "web", {}, depends_on=["aws_subnet.main"]))
        affected = g.get_affected("aws_vpc.main")
        assert "aws_subnet.main" in affected
        assert "aws_instance.web" in affected

    def test_remove_resource(self):
        """Removing a resource also cleans up dependency references."""
        g = ResourceGraph()
        g.add_resource(Resource("aws_vpc", "main", {}))
        g.add_resource(Resource("aws_subnet", "main", {}, depends_on=["aws_vpc.main"]))
        g.remove_resource("aws_vpc.main")
        with pytest.raises(KeyError):
            g.get_resource("aws_vpc.main")
        # Subnet's depends_on should be cleaned up
        subnet = g.get_resource("aws_subnet.main")
        assert "aws_vpc.main" not in subnet.depends_on


# ── StateStore ──


class TestStateStore:
    def test_set_and_get(self):
        """State can be set and retrieved."""
        store = StateStore()
        store.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        state = store.get("aws_vpc.main")
        assert state.properties["cidr"] == "10.0.0.0/16"
        assert state.status == "created"

    def test_set_update(self):
        """Setting an existing resource updates its state."""
        store = StateStore()
        store.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        store.set("aws_vpc.main", {"cidr": "10.1.0.0/16"}, "updated")
        state = store.get("aws_vpc.main")
        assert state.properties["cidr"] == "10.1.0.0/16"
        assert state.status == "updated"

    def test_get_missing(self):
        """Getting a missing resource returns None."""
        store = StateStore()
        assert store.get("aws_vpc.missing") is None

    def test_delete(self):
        """Deleting a resource removes it from the store."""
        store = StateStore()
        store.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        store.delete("aws_vpc.main")
        assert store.get("aws_vpc.main") is None

    def test_list_all(self):
        """All resources can be listed."""
        store = StateStore()
        store.set("aws_vpc.main", {}, "created")
        store.set("aws_subnet.main", {}, "created")
        assert len(store.list_all()) == 2

    def test_serialize_deserialize(self):
        """State can be serialized and deserialized."""
        store = StateStore()
        store.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        data = store.to_dict()
        restored = StateStore.from_dict(data)
        state = restored.get("aws_vpc.main")
        assert state.properties["cidr"] == "10.0.0.0/16"
        assert state.status == "created"


# ── StateLock ──


class TestStateLock:
    def test_acquire(self):
        """Lock can be acquired."""
        lock = StateLock()
        assert lock.acquire("state", "engineer-1") is True
        assert lock.is_locked("state") is True

    def test_release(self):
        """Lock can be released by the owner."""
        lock = StateLock()
        lock.acquire("state", "engineer-1")
        assert lock.release("state", "engineer-1") is True
        assert lock.is_locked("state") is False

    def test_double_acquire_same_owner(self):
        """Same owner can re-acquire their own lock (re-entrant)."""
        lock = StateLock()
        lock.acquire("state", "engineer-1")
        assert lock.acquire("state", "engineer-1") is True

    def test_double_acquire_different_fails(self):
        """Different owner cannot acquire a held lock."""
        lock = StateLock()
        lock.acquire("state", "engineer-1")
        assert lock.acquire("state", "engineer-2") is False

    def test_is_locked(self):
        """is_locked returns correct state."""
        lock = StateLock()
        assert lock.is_locked("state") is False
        lock.acquire("state", "engineer-1")
        assert lock.is_locked("state") is True

    def test_release_wrong_owner_fails(self):
        """Cannot release a lock held by a different owner."""
        lock = StateLock()
        lock.acquire("state", "engineer-1")
        assert lock.release("state", "engineer-2") is False
        assert lock.is_locked("state") is True

    def test_get_lock_info(self):
        """Lock info returns owner and acquired_at."""
        lock = StateLock()
        lock.acquire("state", "engineer-1")
        info = lock.get_lock_info("state")
        assert info["owner"] == "engineer-1"
        assert "acquired_at" in info

    def test_get_lock_info_unlocked(self):
        """Lock info returns None for unlocked resources."""
        lock = StateLock()
        assert lock.get_lock_info("state") is None


# ── DriftDetector ──


class TestDriftDetector:
    def test_no_drift(self):
        """No drift when desired and actual match."""
        dd = DriftDetector()
        desired = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        actual = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        results = dd.detect(desired, actual)
        assert len(results) == 0

    def test_resource_added(self):
        """Resource in desired but not actual is detected as 'added'."""
        dd = DriftDetector()
        desired = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        actual = {}
        results = dd.detect(desired, actual)
        assert len(results) == 1
        assert results[0].drift_type == "added"

    def test_resource_removed(self):
        """Resource in actual but not desired is detected as 'removed'."""
        dd = DriftDetector()
        desired = {}
        actual = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        results = dd.detect(desired, actual)
        assert len(results) == 1
        assert results[0].drift_type == "removed"

    def test_resource_modified(self):
        """Resource with different properties is detected as 'modified'."""
        dd = DriftDetector()
        desired = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        actual = {"aws_vpc.main": {"cidr": "10.1.0.0/16"}}
        results = dd.detect(desired, actual)
        assert len(results) == 1
        assert results[0].drift_type == "modified"

    def test_multiple_drifts(self):
        """Multiple drift types detected simultaneously."""
        dd = DriftDetector()
        desired = {
            "aws_vpc.main": {"cidr": "10.0.0.0/16"},
            "aws_subnet.new": {"az": "us-east-1a"},
        }
        actual = {
            "aws_vpc.main": {"cidr": "10.1.0.0/16"},
            "aws_instance.old": {"type": "t3.micro"},
        }
        results = dd.detect(desired, actual)
        types = {r.drift_type for r in results}
        assert "added" in types     # aws_subnet.new
        assert "removed" in types   # aws_instance.old
        assert "modified" in types  # aws_vpc.main


# ── Module ──


class TestModule:
    def test_validate_inputs_pass(self):
        """Validation passes when all required inputs are provided."""
        mod = Module(
            "vpc",
            variables=[
                Variable("cidr", "string", is_required=True),
                Variable("name", "string", is_required=True),
            ],
        )
        ok, errors = mod.validate_inputs({"cidr": "10.0.0.0/16", "name": "main"})
        assert ok is True
        assert errors == []

    def test_validate_missing_required(self):
        """Validation fails when a required variable is missing."""
        mod = Module(
            "vpc",
            variables=[Variable("cidr", "string", is_required=True)],
        )
        ok, errors = mod.validate_inputs({})
        assert ok is False
        assert any("cidr" in e for e in errors)

    def test_validate_type_mismatch(self):
        """Validation fails when input type doesn't match."""
        mod = Module(
            "vpc",
            variables=[Variable("count", "number", is_required=True)],
        )
        ok, errors = mod.validate_inputs({"count": "not-a-number"})
        assert ok is False
        assert any("type" in e for e in errors)

    def test_get_output(self):
        """Module output can be retrieved by name."""
        mod = Module(
            "vpc",
            outputs=[Output("vpc_id", "vpc-12345")],
        )
        out = mod.get_output("vpc_id")
        assert out is not None
        assert out.value == "vpc-12345"

    def test_get_output_missing(self):
        """Missing output returns None."""
        mod = Module("vpc")
        assert mod.get_output("nonexistent") is None


# ── ModuleComposer ──


class TestModuleComposer:
    def _make_vpc_module(self):
        return Module(
            "vpc",
            variables=[Variable("cidr", "string", is_required=True)],
            outputs=[Output("vpc_id", "vpc-123")],
            resources=[Resource("aws_vpc", "main", {"cidr": "10.0.0.0/16"})],
        )

    def _make_ec2_module(self):
        return Module(
            "ec2",
            variables=[Variable("vpc_id", "string", is_required=True)],
            outputs=[Output("instance_id", "i-abc")],
            resources=[Resource("aws_instance", "web", {"type": "t3.micro"})],
        )

    def test_add_module(self):
        """Modules can be added to the composer."""
        composer = ModuleComposer()
        composer.add_module(self._make_vpc_module(), {"cidr": "10.0.0.0/16"})
        assert "vpc" in composer._modules

    def test_wire(self):
        """Wiring connects module outputs to inputs."""
        composer = ModuleComposer()
        composer.add_module(self._make_vpc_module(), {"cidr": "10.0.0.0/16"})
        composer.add_module(self._make_ec2_module(), {})
        composer.wire("vpc", "vpc_id", "ec2", "vpc_id")
        assert len(composer._wiring) == 1

    def test_compose_combined_graph(self):
        """Composition merges all modules' resources into one graph."""
        composer = ModuleComposer()
        composer.add_module(self._make_vpc_module(), {"cidr": "10.0.0.0/16"})
        composer.add_module(self._make_ec2_module(), {})
        composer.wire("vpc", "vpc_id", "ec2", "vpc_id")
        graph = composer.compose()
        # Should have 2 resources: vpc_main and ec2_web
        order = graph.get_dependency_order()
        assert len(order) == 2

    def test_validate_pass(self):
        """Validation passes when all wiring and inputs are satisfied."""
        composer = ModuleComposer()
        composer.add_module(self._make_vpc_module(), {"cidr": "10.0.0.0/16"})
        composer.add_module(self._make_ec2_module(), {})
        composer.wire("vpc", "vpc_id", "ec2", "vpc_id")
        ok, errors = composer.validate()
        assert ok is True
        assert errors == []

    def test_validate_missing_wire(self):
        """Validation fails when a required input is not provided or wired."""
        composer = ModuleComposer()
        composer.add_module(self._make_vpc_module(), {"cidr": "10.0.0.0/16"})
        composer.add_module(self._make_ec2_module(), {})
        # Not wiring vpc_id to ec2 module
        ok, errors = composer.validate()
        assert ok is False
        assert any("vpc_id" in e for e in errors)


# ── PlanEngine ──


class TestPlanEngine:
    def test_all_create(self):
        """All resources in desired but not in state are CREATE actions."""
        engine = PlanEngine()
        desired = {
            "aws_vpc.main": {"cidr": "10.0.0.0/16"},
            "aws_subnet.a": {"az": "us-east-1a"},
        }
        state = StateStore()
        plan = engine.plan(desired, state)
        assert plan.summary()["create"] == 2

    def test_all_delete(self):
        """Resources in state but not desired are DELETE actions."""
        engine = PlanEngine()
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        state.set("aws_subnet.a", {"az": "us-east-1a"}, "created")
        plan = engine.plan({}, state)
        assert plan.summary()["delete"] == 2

    def test_update_changed(self):
        """Resources with changed properties are UPDATE actions."""
        engine = PlanEngine()
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        desired = {"aws_vpc.main": {"cidr": "10.1.0.0/16"}}
        plan = engine.plan(desired, state)
        assert plan.summary()["update"] == 1

    def test_no_changes(self):
        """Identical state and desired produce only NO_OP actions."""
        engine = PlanEngine()
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        desired = {"aws_vpc.main": {"cidr": "10.0.0.0/16"}}
        plan = engine.plan(desired, state)
        assert plan.has_changes() is False
        assert plan.summary()["no_op"] == 1

    def test_mixed_plan(self):
        """Mixed plan with create, update, delete, and no_op."""
        engine = PlanEngine()
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")  # unchanged
        state.set("aws_subnet.old", {"az": "us-east-1a"}, "created")    # to delete
        state.set("aws_instance.web", {"type": "t3.micro"}, "created")   # to update

        desired = {
            "aws_vpc.main": {"cidr": "10.0.0.0/16"},      # no_op
            "aws_instance.web": {"type": "t3.large"},       # update
            "aws_s3.bucket": {"name": "my-bucket"},         # create
        }
        plan = engine.plan(desired, state)
        summary = plan.summary()
        assert summary["create"] == 1
        assert summary["update"] == 1
        assert summary["delete"] == 1
        assert summary["no_op"] == 1


# ── Plan ──


class TestPlan:
    def test_has_changes_true(self):
        """Plan with CREATE actions has changes."""
        plan = Plan([Action("r1", ActionType.CREATE, new_properties={})])
        assert plan.has_changes() is True

    def test_has_changes_false(self):
        """Plan with only NO_OP has no changes."""
        plan = Plan([Action("r1", ActionType.NO_OP)])
        assert plan.has_changes() is False

    def test_get_actions_filtered(self):
        """Actions can be filtered by type."""
        plan = Plan([
            Action("r1", ActionType.CREATE),
            Action("r2", ActionType.DELETE),
            Action("r3", ActionType.CREATE),
        ])
        creates = plan.get_actions(ActionType.CREATE)
        assert len(creates) == 2

    def test_get_actions_unfiltered(self):
        """All actions returned when no filter specified."""
        plan = Plan([
            Action("r1", ActionType.CREATE),
            Action("r2", ActionType.DELETE),
        ])
        assert len(plan.get_actions()) == 2


# ── ApplyEngine ──


class TestApplyEngine:
    def test_apply_creates(self):
        """Apply creates resources in the state store."""
        state = StateStore()
        plan = Plan([
            Action("aws_vpc.main", ActionType.CREATE, new_properties={"cidr": "10.0.0.0/16"}),
        ])
        engine = ApplyEngine()
        result = engine.apply(plan, state)
        assert len(result.succeeded) == 1
        assert state.get("aws_vpc.main").status == "created"

    def test_apply_updates_state(self):
        """Apply updates existing resources in the state store."""
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        plan = Plan([
            Action("aws_vpc.main", ActionType.UPDATE,
                   old_properties={"cidr": "10.0.0.0/16"},
                   new_properties={"cidr": "10.1.0.0/16"}),
        ])
        engine = ApplyEngine()
        engine.apply(plan, state)
        assert state.get("aws_vpc.main").properties["cidr"] == "10.1.0.0/16"
        assert state.get("aws_vpc.main").status == "updated"

    def test_apply_deletes(self):
        """Apply removes deleted resources from the state store."""
        state = StateStore()
        state.set("aws_vpc.main", {"cidr": "10.0.0.0/16"}, "created")
        plan = Plan([
            Action("aws_vpc.main", ActionType.DELETE, old_properties={"cidr": "10.0.0.0/16"}),
        ])
        engine = ApplyEngine()
        engine.apply(plan, state)
        assert state.get("aws_vpc.main") is None

    def test_apply_in_order(self):
        """Apply respects dependency order when provided."""
        state = StateStore()
        plan = Plan([
            Action("aws_instance.web", ActionType.CREATE, new_properties={"type": "t3.micro"}),
            Action("aws_vpc.main", ActionType.CREATE, new_properties={"cidr": "10.0.0.0/16"}),
        ])
        engine = ApplyEngine()
        result = engine.apply(plan, state, dependency_order=["aws_vpc.main", "aws_instance.web"])
        # Both should succeed, VPC created first
        assert len(result.succeeded) == 2
        # Verify order: VPC should be first in succeeded
        assert result.succeeded[0].resource_id == "aws_vpc.main"
        assert result.succeeded[1].resource_id == "aws_instance.web"

    def test_apply_result(self):
        """ApplyResult contains succeeded list and final state."""
        state = StateStore()
        plan = Plan([
            Action("aws_vpc.main", ActionType.CREATE, new_properties={"cidr": "10.0.0.0/16"}),
            Action("aws_subnet.a", ActionType.CREATE, new_properties={"az": "us-east-1a"}),
        ])
        engine = ApplyEngine()
        result = engine.apply(plan, state)
        assert len(result.succeeded) == 2
        assert len(result.failed) == 0
        assert result.state is state
