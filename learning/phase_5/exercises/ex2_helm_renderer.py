"""
Exercise 2: Helm Template Renderer
========================================
Implement a simplified Helm template renderer that substitutes Go-style
template expressions with values from a dictionary.

WHY THIS MATTERS:
Helm charts are the primary way to package and deploy applications on
Kubernetes. Understanding how template rendering works gives you insight
into how a single chart can generate different Kubernetes manifests for
dev, staging, and production environments.

Template syntax to support:
  {{ .Values.key }}              — simple value substitution
  {{ .Values.nested.key }}       — dot-path navigation into nested dicts
  {{ if .Values.key }}...{{ end }} — conditional blocks (truthy/falsy)

YOUR TASK:
1. Implement _resolve(path, values) — navigate a dot-separated path
2. Implement _render_conditionals(template, values) — process if/end blocks
3. Implement render(template, values) — full rendering pipeline
"""

import re


class HelmRenderer:
    """Simplified Helm template renderer.

    Supports value substitution and conditional blocks using Go-style
    template syntax.

    TODO: Implement these methods:

    1. _resolve(path, values) -> value or None
       Navigate a dot-separated path (e.g. "image.repository") through
       a nested dictionary. Return None if any key is missing.

       Example:
         _resolve("image.repository", {"image": {"repository": "nginx"}})
         -> "nginx"
         _resolve("missing.key", {"image": {"repository": "nginx"}})
         -> None

    2. _render_conditionals(template, values) -> str
       Process {{ if .Values.key }}...{{ end }} blocks.
       If the value is truthy (not None, False, 0, or ""), keep the
       content between if and end. Otherwise, remove it.

       Use re.sub with a regex pattern to find and replace if/end blocks.
       Pattern hint: r'\\{\\{\\s*if\\s+\\.Values\\.(\\w+)\\s*\\}\\}(.*?)\\{\\{\\s*end\\s*\\}\\}'
       Use re.DOTALL flag so . matches newlines.

    3. render(template, values) -> str
       Full rendering pipeline:
       a. First process conditionals (_render_conditionals)
       b. Then substitute {{ .Values.xxx }} expressions
       Use re.sub to find {{ .Values.path }} and replace with resolved values.
       If value is None, replace with empty string.
    """

    def _resolve(self, path: str, values: dict):
        # YOUR CODE HERE (~5 lines)
        # Navigate dot-separated path through nested dict
        raise NotImplementedError("Implement _resolve")

    def _render_conditionals(self, template: str, values: dict) -> str:
        # YOUR CODE HERE (~8 lines)
        # Use regex to find {{ if .Values.key }}...{{ end }} blocks
        # Keep content if value is truthy, remove otherwise
        raise NotImplementedError("Implement _render_conditionals")

    def render(self, template: str, values: dict) -> str:
        # YOUR CODE HERE (~8 lines)
        # 1. Process conditionals
        # 2. Substitute {{ .Values.xxx }} with resolved values
        raise NotImplementedError("Implement render")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    renderer = HelmRenderer()

    # Test 1: Simple substitution
    result = renderer.render("name: {{ .Values.app }}", {"app": "web"})
    assert result == "name: web", f"Expected 'name: web', got '{result}'"
    print("[PASS] Simple substitution")

    # Test 2: Nested value
    result = renderer.render(
        "image: {{ .Values.image.repository }}",
        {"image": {"repository": "nginx"}},
    )
    assert result == "image: nginx", f"Expected 'image: nginx', got '{result}'"
    print("[PASS] Nested value")

    # Test 3: Missing value renders empty
    result = renderer.render("port: {{ .Values.port }}", {})
    assert result == "port: ", f"Expected 'port: ', got '{result}'"
    print("[PASS] Missing value")

    # Test 4: Conditional true
    result = renderer.render(
        "{{ if .Values.debug }}DEBUG_MODE{{ end }}",
        {"debug": True},
    )
    assert result == "DEBUG_MODE", f"Expected 'DEBUG_MODE', got '{result}'"
    print("[PASS] Conditional true")

    # Test 5: Conditional false
    result = renderer.render(
        "{{ if .Values.debug }}DEBUG_MODE{{ end }}",
        {"debug": False},
    )
    assert result == "", f"Expected '', got '{result}'"
    print("[PASS] Conditional false")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
