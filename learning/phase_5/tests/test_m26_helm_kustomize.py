"""
Tests for M26: Helm & Kustomize — template rendering, values merging,
patching strategies, and environment promotion.
"""

import pytest

from m26_helm_kustomize.helm_template import TemplateEngine
from m26_helm_kustomize.values_override import ValuesHierarchy, SemVer
from m26_helm_kustomize.kustomize_overlay import (
    StrategicMergePatch,
    JsonPatch,
    KustomizeOverlay,
)
from m26_helm_kustomize.environment_promotion import (
    PromotionGate,
    EnvironmentPipeline,
)


# ── TemplateEngine ──


class TestTemplateEngine:
    def test_simple_value_substitution(self):
        engine = TemplateEngine()
        result = engine.render("Hello {{ .Values.name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_nested_value(self):
        engine = TemplateEngine()
        result = engine.render(
            "Image: {{ .Values.image.repository }}",
            {"image": {"repository": "nginx"}},
        )
        assert result == "Image: nginx"

    def test_missing_value_renders_empty(self):
        engine = TemplateEngine()
        result = engine.render("Port: {{ .Values.port }}", {})
        assert result == "Port: "

    def test_if_true(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ if .Values.enabled }}ON{{ end }}",
            {"enabled": True},
        )
        assert result == "ON"

    def test_if_false(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ if .Values.enabled }}ON{{ end }}",
            {"enabled": False},
        )
        assert result == ""

    def test_if_else(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ if .Values.debug }}DEBUG{{ else }}RELEASE{{ end }}",
            {"debug": False},
        )
        assert result == "RELEASE"

    def test_range_list(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ range .Values.ports }}{{ . }} {{ end }}",
            {"ports": [80, 443, 8080]},
        )
        assert result == "80 443 8080 "

    def test_range_empty_list(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ range .Values.items }}{{ . }}{{ end }}",
            {"items": []},
        )
        assert result == ""

    def test_pipe_default(self):
        engine = TemplateEngine()
        result = engine.render(
            'Port: {{ .Values.port | default "8080" }}',
            {},
        )
        assert result == "Port: 8080"

    def test_pipe_default_not_needed(self):
        engine = TemplateEngine()
        result = engine.render(
            '{{ .Values.port | default "8080" }}',
            {"port": 3000},
        )
        assert result == "3000"

    def test_pipe_quote(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ .Values.name | quote }}",
            {"name": "myapp"},
        )
        assert result == '"myapp"'

    def test_pipe_upper(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ .Values.env | upper }}",
            {"env": "production"},
        )
        assert result == "PRODUCTION"

    def test_pipe_lower(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ .Values.name | lower }}",
            {"name": "MyApp"},
        )
        assert result == "myapp"

    def test_pipe_indent(self):
        engine = TemplateEngine()
        result = engine.render(
            "{{ .Values.text | indent 4 }}",
            {"text": "line1\nline2"},
        )
        assert result == "    line1\n    line2"

    def test_include_named_template(self):
        engine = TemplateEngine()
        engine.define("labels", "app: {{ .Values.app }}")
        result = engine.render(
            'metadata:\n  {{ include "labels" . }}',
            {"app": "web"},
        )
        assert "app: web" in result


# ── ValuesHierarchy ──


class TestValuesHierarchy:
    def test_shallow_merge(self):
        vh = ValuesHierarchy()
        result = vh.merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_deep_merge(self):
        vh = ValuesHierarchy()
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 9, "z": 3}}
        result = vh.merge(base, override)
        assert result == {"a": {"x": 1, "y": 9, "z": 3}}

    def test_override_replaces_non_dict(self):
        vh = ValuesHierarchy()
        result = vh.merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_resolve_precedence(self):
        """cli_sets should override everything."""
        vh = ValuesHierarchy()
        result = vh.resolve(
            chart_defaults={"replicas": 1, "image": "nginx"},
            parent_values={"replicas": 2},
            user_values={"replicas": 3},
            cli_sets={"replicas": 5},
        )
        assert result["replicas"] == 5
        assert result["image"] == "nginx"

    def test_resolve_user_values_override_parent(self):
        vh = ValuesHierarchy()
        result = vh.resolve(
            chart_defaults={"a": 1},
            parent_values={"a": 2},
            user_values={"a": 3},
            cli_sets={},
        )
        assert result["a"] == 3

    def test_merge_does_not_mutate_inputs(self):
        vh = ValuesHierarchy()
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        vh.merge(base, override)
        assert base == {"a": {"x": 1}}
        assert override == {"a": {"y": 2}}


# ── SemVer ──


class TestSemVer:
    def test_parse(self):
        v = SemVer.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_v_prefix(self):
        v = SemVer.parse("v2.0.1")
        assert v.major == 2

    def test_compare_less_than(self):
        assert SemVer.parse("1.2.3") < SemVer.parse("1.2.4")
        assert SemVer.parse("1.2.3") < SemVer.parse("1.3.0")
        assert SemVer.parse("1.2.3") < SemVer.parse("2.0.0")

    def test_compare_greater_than(self):
        assert SemVer.parse("2.0.0") > SemVer.parse("1.9.9")

    def test_compare_equal(self):
        assert SemVer.parse("1.2.3") == SemVer.parse("1.2.3")

    def test_bump_major(self):
        v = SemVer.parse("1.2.3").bump_major()
        assert str(v) == "2.0.0"

    def test_bump_minor(self):
        v = SemVer.parse("1.2.3").bump_minor()
        assert str(v) == "1.3.0"

    def test_bump_patch(self):
        v = SemVer.parse("1.2.3").bump_patch()
        assert str(v) == "1.2.4"

    def test_invalid_parse(self):
        with pytest.raises(ValueError):
            SemVer.parse("1.2")


# ── StrategicMergePatch ──


class TestStrategicMergePatch:
    def test_simple_override(self):
        smp = StrategicMergePatch()
        result = smp.apply({"replicas": 1}, {"replicas": 3})
        assert result == {"replicas": 3}

    def test_nested_merge(self):
        smp = StrategicMergePatch()
        base = {"metadata": {"name": "app", "labels": {"v": "1"}}}
        patch = {"metadata": {"labels": {"env": "prod"}}}
        result = smp.apply(base, patch)
        assert result["metadata"]["name"] == "app"
        assert result["metadata"]["labels"]["v"] == "1"
        assert result["metadata"]["labels"]["env"] == "prod"

    def test_delete_with_none(self):
        smp = StrategicMergePatch()
        base = {"a": 1, "b": 2, "c": 3}
        patch = {"b": None}
        result = smp.apply(base, patch)
        assert result == {"a": 1, "c": 3}

    def test_add_new_key(self):
        smp = StrategicMergePatch()
        result = smp.apply({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        smp = StrategicMergePatch()
        base = {"a": {"x": 1}}
        smp.apply(base, {"a": {"y": 2}})
        assert base == {"a": {"x": 1}}


# ── JsonPatch ──


class TestJsonPatch:
    def test_add(self):
        jp = JsonPatch()
        result = jp.apply(
            {"a": 1},
            [{"op": "add", "path": "/b", "value": 2}],
        )
        assert result == {"a": 1, "b": 2}

    def test_remove(self):
        jp = JsonPatch()
        result = jp.apply(
            {"a": 1, "b": 2},
            [{"op": "remove", "path": "/b"}],
        )
        assert result == {"a": 1}

    def test_replace(self):
        jp = JsonPatch()
        result = jp.apply(
            {"a": 1},
            [{"op": "replace", "path": "/a", "value": 99}],
        )
        assert result == {"a": 99}

    def test_move(self):
        jp = JsonPatch()
        result = jp.apply(
            {"a": 1, "b": 2},
            [{"op": "move", "from": "/a", "path": "/c"}],
        )
        assert result == {"b": 2, "c": 1}

    def test_nested_path(self):
        jp = JsonPatch()
        result = jp.apply(
            {"metadata": {"labels": {}}},
            [{"op": "add", "path": "/metadata/labels/app", "value": "web"}],
        )
        assert result["metadata"]["labels"]["app"] == "web"

    def test_test_operation_passes(self):
        jp = JsonPatch()
        # Should not raise
        result = jp.apply(
            {"a": 1},
            [
                {"op": "test", "path": "/a", "value": 1},
                {"op": "replace", "path": "/a", "value": 2},
            ],
        )
        assert result["a"] == 2

    def test_test_operation_fails(self):
        jp = JsonPatch()
        with pytest.raises(KeyError, match="Test failed"):
            jp.apply(
                {"a": 1},
                [{"op": "test", "path": "/a", "value": 99}],
            )


# ── KustomizeOverlay ──


class TestKustomizeOverlay:
    def test_single_patch(self):
        base = {"replicas": 1, "image": "nginx:1.21"}
        smp = StrategicMergePatch()
        overlay = KustomizeOverlay(base)
        overlay.add_patch(smp, {"replicas": 3})
        result = overlay.build()
        assert result["replicas"] == 3
        assert result["image"] == "nginx:1.21"

    def test_multiple_patches_in_order(self):
        base = {"replicas": 1}
        smp = StrategicMergePatch()
        overlay = KustomizeOverlay(base)
        overlay.add_patch(smp, {"replicas": 3})
        overlay.add_patch(smp, {"replicas": 5})
        result = overlay.build()
        assert result["replicas"] == 5

    def test_mixed_patch_types(self):
        base = {"metadata": {"name": "app"}, "replicas": 1}
        smp = StrategicMergePatch()
        jp = JsonPatch()
        overlay = KustomizeOverlay(base)
        overlay.add_patch(smp, {"replicas": 3})
        overlay.add_patch(jp, [{"op": "add", "path": "/metadata/labels", "value": {"env": "prod"}}])
        result = overlay.build()
        assert result["replicas"] == 3
        assert result["metadata"]["labels"]["env"] == "prod"


# ── EnvironmentPipeline ──


class TestEnvironmentPipeline:
    def test_promote_dev_to_staging(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        result = pipeline.promote("1.0.0", "dev", "staging")
        assert result.success is True
        assert pipeline.get_version("staging") == "1.0.0"

    def test_promote_with_passing_gate(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        gate = PromotionGate("tests", lambda: True, is_required=True)
        pipeline.add_gate("dev", "staging", gate)
        result = pipeline.promote("1.0.0", "dev", "staging")
        assert result.success is True

    def test_promote_with_failed_required_gate(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        gate = PromotionGate("security-scan", lambda: False, is_required=True)
        pipeline.add_gate("dev", "staging", gate)
        result = pipeline.promote("1.0.0", "dev", "staging")
        assert result.success is False
        assert "security-scan" in result.failed_gates

    def test_promote_with_failed_optional_gate(self):
        """Optional gate failure should NOT block promotion."""
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        gate = PromotionGate("code-coverage", lambda: False, is_required=False)
        pipeline.add_gate("dev", "staging", gate)
        result = pipeline.promote("1.0.0", "dev", "staging")
        assert result.success is True

    def test_can_promote_returns_failed_gates(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        pipeline.add_gate(
            "dev", "staging",
            PromotionGate("gate-a", lambda: False, is_required=True),
        )
        pipeline.add_gate(
            "dev", "staging",
            PromotionGate("gate-b", lambda: False, is_required=True),
        )
        can, failed = pipeline.can_promote("dev", "staging")
        assert can is False
        assert set(failed) == {"gate-a", "gate-b"}

    def test_version_tracking(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        assert pipeline.get_version("staging") is None
        pipeline.promote("1.0.0", "dev", "staging")
        assert pipeline.get_version("staging") == "1.0.0"
        pipeline.promote("1.1.0", "dev", "staging")
        assert pipeline.get_version("staging") == "1.1.0"

    def test_failed_promotion_does_not_update_version(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        pipeline.add_gate(
            "staging", "production",
            PromotionGate("approval", lambda: False, is_required=True),
        )
        pipeline.promote("1.0.0", "dev", "staging")
        pipeline.promote("1.0.0", "staging", "production")
        assert pipeline.get_version("production") is None

    def test_history(self):
        pipeline = EnvironmentPipeline(["dev", "staging", "production"])
        pipeline.promote("1.0.0", "dev", "staging")
        pipeline.promote("1.1.0", "dev", "staging")
        history = pipeline.get_history("staging")
        assert len(history) == 2
        assert history[0].artifact_version == "1.0.0"
        assert history[1].artifact_version == "1.1.0"
