"""
Tests for M27: CI/CD Pipeline Design — pipeline DAGs, deployment strategies,
artifact management, and rollback decision engines.
"""

from datetime import datetime

import pytest

from m27_cicd.pipeline_stages import StageStatus, PipelineStage, Pipeline
from m27_cicd.deployment_strategies import (
    BlueGreenDeployment,
    CanaryDeployment,
    RollingDeployment,
)
from m27_cicd.artifact_management import Artifact, ArtifactRegistry
from m27_cicd.rollback import (
    RollbackCondition,
    RollbackDecisionEngine,
    RollbackAction,
    RollbackHistory,
)


# ── Pipeline ──


class TestPipeline:
    def test_add_stages(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test"])
        assert len(p._stages) == 3

    def test_validate_valid_pipeline(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test"])
        is_valid, errors = p.validate()
        assert is_valid is True
        assert errors == []

    def test_validate_cycle_detection(self):
        p = Pipeline()
        p.add_stage("a", dependencies=["b"])
        p.add_stage("b", dependencies=["a"])
        is_valid, errors = p.validate()
        assert is_valid is False
        assert any("cycle" in e.lower() for e in errors)

    def test_validate_missing_dependency(self):
        p = Pipeline()
        p.add_stage("test", dependencies=["build"])
        is_valid, errors = p.validate()
        assert is_valid is False
        assert any("unknown" in e.lower() for e in errors)

    def test_execution_order_linear(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test"])
        waves = p.get_execution_order()
        assert waves == [["build"], ["test"], ["deploy"]]

    def test_execution_order_parallel(self):
        """Stages with no dependency on each other run in the same wave."""
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("unit-test", dependencies=["build"])
        p.add_stage("lint", dependencies=["build"])
        p.add_stage("deploy", dependencies=["unit-test", "lint"])
        waves = p.get_execution_order()
        assert waves[0] == ["build"]
        assert sorted(waves[1]) == ["lint", "unit-test"]
        assert waves[2] == ["deploy"]

    def test_parallel_groups(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        groups = p.get_parallel_groups()
        assert "wave 1" in groups
        assert "wave 2" in groups
        assert groups["wave 1"] == ["build"]
        assert groups["wave 2"] == ["test"]

    def test_run_all_succeed(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test"])
        results = p.run()
        assert results["build"] == StageStatus.SUCCESS
        assert results["test"] == StageStatus.SUCCESS
        assert results["deploy"] == StageStatus.SUCCESS

    def test_run_with_failure_skips_dependents(self):
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test"])
        results = p.run_with_failure("test")
        assert results["build"] == StageStatus.SUCCESS
        assert results["test"] == StageStatus.FAILED
        assert results["deploy"] == StageStatus.SKIPPED

    def test_run_with_failure_parallel_partial_skip(self):
        """Only stages depending on the failed stage are skipped."""
        p = Pipeline()
        p.add_stage("build")
        p.add_stage("test", dependencies=["build"])
        p.add_stage("lint", dependencies=["build"])
        p.add_stage("deploy", dependencies=["test", "lint"])
        results = p.run_with_failure("test")
        assert results["build"] == StageStatus.SUCCESS
        assert results["test"] == StageStatus.FAILED
        assert results["lint"] == StageStatus.SUCCESS
        assert results["deploy"] == StageStatus.SKIPPED


# ── BlueGreenDeployment ──


class TestBlueGreenDeployment:
    def test_initial_state(self):
        bg = BlueGreenDeployment("1.0.0")
        assert bg.get_active_version() == "1.0.0"
        assert bg.get_inactive_version() is None

    def test_deploy_to_inactive(self):
        bg = BlueGreenDeployment("1.0.0")
        env = bg.deploy("2.0.0")
        assert env == "green"
        assert bg.get_active_version() == "1.0.0"

    def test_switch_traffic(self):
        bg = BlueGreenDeployment("1.0.0")
        bg.deploy("2.0.0")
        bg.switch_traffic()
        assert bg.get_active_version() == "2.0.0"

    def test_rollback(self):
        bg = BlueGreenDeployment("1.0.0")
        bg.deploy("2.0.0")
        bg.switch_traffic()
        assert bg.get_active_version() == "2.0.0"
        bg.rollback()
        assert bg.get_active_version() == "1.0.0"

    def test_multiple_deploys(self):
        bg = BlueGreenDeployment("1.0.0")
        bg.deploy("2.0.0")
        bg.switch_traffic()
        bg.deploy("3.0.0")
        bg.switch_traffic()
        assert bg.get_active_version() == "3.0.0"


# ── CanaryDeployment ──


class TestCanaryDeployment:
    def test_deploy_canary(self):
        cd = CanaryDeployment("1.0.0", step_size=10)
        cd.deploy_canary("2.0.0")
        assert cd.canary_version == "2.0.0"
        assert cd.canary_percentage == 10

    def test_increase_traffic(self):
        cd = CanaryDeployment("1.0.0", step_size=10)
        cd.deploy_canary("2.0.0")
        new_pct = cd.increase_traffic()
        assert new_pct == 20

    def test_increase_traffic_custom_step(self):
        cd = CanaryDeployment("1.0.0", step_size=10)
        cd.deploy_canary("2.0.0")
        new_pct = cd.increase_traffic(step=40)
        assert new_pct == 50

    def test_promote(self):
        cd = CanaryDeployment("1.0.0", step_size=10)
        cd.deploy_canary("2.0.0")
        cd.promote()
        assert cd.stable_version == "2.0.0"
        assert cd.canary_version is None
        assert cd.canary_percentage == 0

    def test_rollback(self):
        cd = CanaryDeployment("1.0.0", step_size=10)
        cd.deploy_canary("2.0.0")
        cd.increase_traffic()
        cd.rollback()
        assert cd.canary_version is None
        assert cd.canary_percentage == 0
        assert cd.stable_version == "1.0.0"

    def test_traffic_split_math(self):
        cd = CanaryDeployment("1.0.0", step_size=25)
        cd.deploy_canary("2.0.0")
        split = cd.get_traffic_split()
        assert split["stable"] == 75
        assert split["canary"] == 25

    def test_traffic_does_not_exceed_100(self):
        cd = CanaryDeployment("1.0.0", step_size=60)
        cd.deploy_canary("2.0.0")
        cd.increase_traffic()
        assert cd.canary_percentage == 100


# ── RollingDeployment ──


class TestRollingDeployment:
    def test_deploy_next_batch(self):
        rd = RollingDeployment(["i1", "i2", "i3", "i4"], "1.0.0", batch_size=2)
        rd.deploy("2.0.0")
        updated = rd.deploy_next_batch()
        assert updated == ["i1", "i2"]
        assert not rd.is_complete()

    def test_deploy_all_batches(self):
        rd = RollingDeployment(["i1", "i2", "i3", "i4"], "1.0.0", batch_size=2)
        rd.deploy("2.0.0")
        rd.deploy_next_batch()
        rd.deploy_next_batch()
        assert rd.is_complete()

    def test_progress_tracking(self):
        rd = RollingDeployment(["i1", "i2", "i3", "i4"], "1.0.0", batch_size=2)
        rd.deploy("2.0.0")
        rd.deploy_next_batch()
        prog = rd.get_progress()
        assert prog["updated"] == 2
        assert prog["total"] == 4
        assert prog["percent"] == 50.0

    def test_rollback_mid_deploy(self):
        rd = RollingDeployment(["i1", "i2", "i3", "i4"], "1.0.0", batch_size=2)
        rd.deploy("2.0.0")
        rd.deploy_next_batch()
        rd.rollback()
        prog = rd.get_progress()
        assert prog["updated"] == 4
        assert prog["percent"] == 100.0
        # All instances back to original version
        assert all(v == "1.0.0" for v in rd._instance_versions.values())

    def test_single_batch_size(self):
        rd = RollingDeployment(["i1", "i2", "i3"], "1.0.0", batch_size=1)
        rd.deploy("2.0.0")
        rd.deploy_next_batch()
        prog = rd.get_progress()
        assert prog["updated"] == 1


# ── ArtifactRegistry ──


class TestArtifactRegistry:
    def test_publish_and_get(self):
        registry = ArtifactRegistry()
        artifact = Artifact(name="api", version="1.0.0")
        registry.publish(artifact)
        result = registry.get("api", "1.0.0")
        assert result.version == "1.0.0"

    def test_get_latest(self):
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="api", version="1.0.0"))
        registry.publish(Artifact(name="api", version="1.1.0"))
        registry.publish(Artifact(name="api", version="1.0.5"))
        latest = registry.get_latest("api")
        assert latest.version == "1.1.0"

    def test_get_without_version_returns_latest(self):
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="api", version="1.0.0"))
        registry.publish(Artifact(name="api", version="2.0.0"))
        result = registry.get("api")
        assert result.version == "2.0.0"

    def test_list_versions_sorted(self):
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="api", version="2.0.0"))
        registry.publish(Artifact(name="api", version="1.0.0"))
        registry.publish(Artifact(name="api", version="1.5.0"))
        versions = [a.version for a in registry.list("api")]
        assert versions == ["1.0.0", "1.5.0", "2.0.0"]

    def test_delete_version(self):
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="api", version="1.0.0"))
        registry.publish(Artifact(name="api", version="2.0.0"))
        registry.delete("api", "1.0.0")
        versions = [a.version for a in registry.list("api")]
        assert versions == ["2.0.0"]

    def test_publish_duplicate_raises(self):
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="api", version="1.0.0"))
        with pytest.raises(ValueError, match="already exists"):
            registry.publish(Artifact(name="api", version="1.0.0"))

    def test_get_nonexistent_raises(self):
        registry = ArtifactRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_version_ordering(self):
        """SemVer ordering: 1.2.3 < 1.10.0 < 2.0.0."""
        registry = ArtifactRegistry()
        registry.publish(Artifact(name="lib", version="1.10.0"))
        registry.publish(Artifact(name="lib", version="2.0.0"))
        registry.publish(Artifact(name="lib", version="1.2.3"))
        latest = registry.get_latest("lib")
        assert latest.version == "2.0.0"


# ── RollbackDecisionEngine ──


class TestRollbackDecisionEngine:
    def test_no_conditions_no_rollback(self):
        engine = RollbackDecisionEngine()
        should, reasons = engine.should_rollback({"error_rate": 0.5})
        assert should is False
        assert reasons == []

    def test_single_threshold_breach(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("error_rate", "gt", 0.01))
        should, reasons = engine.should_rollback({"error_rate": 0.05})
        assert should is True
        assert len(reasons) == 1

    def test_multiple_conditions_one_breach(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("error_rate", "gt", 0.01))
        engine.add_condition(RollbackCondition("p99_latency_ms", "gt", 500))
        should, reasons = engine.should_rollback(
            {"error_rate": 0.001, "p99_latency_ms": 800}
        )
        assert should is True
        assert len(reasons) == 1

    def test_all_conditions_pass(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("error_rate", "gt", 0.01))
        engine.add_condition(RollbackCondition("p99_latency_ms", "gt", 500))
        should, reasons = engine.should_rollback(
            {"error_rate": 0.001, "p99_latency_ms": 100}
        )
        assert should is False
        assert reasons == []

    def test_lt_operator(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("availability", "lt", 0.99))
        should, reasons = engine.should_rollback({"availability": 0.95})
        assert should is True

    def test_gte_operator(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("cpu_pct", "gte", 90))
        should, _ = engine.should_rollback({"cpu_pct": 90})
        assert should is True

    def test_missing_metric_ignored(self):
        engine = RollbackDecisionEngine()
        engine.add_condition(RollbackCondition("error_rate", "gt", 0.01))
        should, reasons = engine.should_rollback({"cpu_pct": 50})
        assert should is False


# ── RollbackHistory ──


class TestRollbackHistory:
    def test_add_and_get_recent(self):
        history = RollbackHistory()
        action = RollbackAction("2.0.0", "1.0.0", "high error rate")
        history.add(action)
        recent = history.get_recent(5)
        assert len(recent) == 1
        assert recent[0].version_from == "2.0.0"

    def test_get_recent_limits(self):
        history = RollbackHistory()
        for i in range(20):
            history.add(RollbackAction(f"{i+1}.0.0", f"{i}.0.0", "test"))
        recent = history.get_recent(5)
        assert len(recent) == 5
        assert recent[-1].version_from == "20.0.0"

    def test_stats(self):
        history = RollbackHistory()
        history.add(RollbackAction("2.0.0", "1.0.0", "auto", is_automatic=True))
        history.add(RollbackAction("3.0.0", "2.0.0", "auto", is_automatic=True))
        history.add(RollbackAction("4.0.0", "3.0.0", "manual", is_automatic=False))
        stats = history.get_stats()
        assert stats["total"] == 3
        assert stats["automatic"] == 2
        assert stats["manual"] == 1

    def test_empty_stats(self):
        history = RollbackHistory()
        stats = history.get_stats()
        assert stats["total"] == 0
        assert stats["automatic"] == 0
        assert stats["manual"] == 0
