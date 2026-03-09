"""
Helm Template Engine — Go-style template rendering for Kubernetes manifests.

WHY THIS MATTERS:
Helm is the de facto package manager for Kubernetes. Helm charts use
Go templates to parameterize Kubernetes YAML manifests. Instead of
maintaining separate YAML files for dev, staging, and production, you
write one template and supply different values.

Template syntax (subset implemented here):
  {{ .Values.key }}              — value substitution
  {{ .Values.nested.key }}       — dot-path navigation
  {{ if .Values.enabled }}...{{ else }}...{{ end }}  — conditional blocks
  {{ range .Values.items }}...{{ end }}              — iteration
  {{ .Values.x | default "y" }} — default value if missing/empty
  {{ .Values.x | quote }}        — wrap in double quotes
  {{ .Values.x | upper }}        — uppercase
  {{ .Values.x | lower }}        — lowercase
  {{ .Values.x | indent N }}     — indent each line by N spaces
  {{ include "name" . }}         — include a named template

This implementation uses regex-based parsing (no external deps) to
demonstrate how Helm's template engine works under the hood.
"""

import re
from typing import Any


class TemplateEngine:
    """Renders Go-style templates with a values dictionary.

    The engine processes templates in multiple passes:
      1. Named template definitions ({{ define "name" }}...{{ end }})
      2. Include directives ({{ include "name" . }})
      3. Range loops ({{ range .Values.list }}...{{ end }})
      4. Conditionals ({{ if }}...{{ else }}...{{ end }})
      5. Value substitutions with pipe functions

    WHY MULTIPLE PASSES:
    Helm processes templates in a specific order so that includes are
    resolved before conditionals, and conditionals before values. This
    ensures that included templates can themselves contain conditionals
    and value references.
    """

    def __init__(self):
        self._named_templates: dict[str, str] = {}

    def define(self, name: str, template: str) -> None:
        """Register a named template for use with {{ include }}."""
        self._named_templates[name] = template

    def render(self, template: str, values: dict) -> str:
        """Render a template string with the given values dictionary.

        Args:
            template: Go-style template string.
            values: Dictionary of values accessible via .Values.xxx.

        Returns:
            The rendered string with all substitutions applied.
        """
        result = template

        # Pass 1: Process {{ include "name" . }}
        result = self._process_includes(result, values)

        # Pass 2: Process {{ range .Values.list }}...{{ end }}
        result = self._process_ranges(result, values)

        # Pass 3: Process {{ if .Values.key }}...{{ else }}...{{ end }}
        result = self._process_conditionals(result, values)

        # Pass 4: Process {{ .Values.key | pipe }} substitutions
        result = self._process_values(result, values)

        return result

    def _resolve_path(self, path: str, values: dict) -> Any:
        """Resolve a dot-separated path like 'nested.key' in a dict.

        Returns None if any segment is missing.
        """
        parts = path.split(".")
        current: Any = values
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _process_includes(self, template: str, values: dict) -> str:
        """Replace {{ include "name" . }} with the named template content."""
        pattern = r'\{\{\s*include\s+"([^"]+)"\s+\.\s*\}\}'

        def replacer(match: re.Match) -> str:
            name = match.group(1)
            if name in self._named_templates:
                # Recursively render the included template
                return self.render(self._named_templates[name], values)
            return match.group(0)  # Leave unchanged if not found

        return re.sub(pattern, replacer, template)

    def _process_ranges(self, template: str, values: dict) -> str:
        """Process {{ range .Values.list }}...{{ end }} blocks.

        Inside the range block, {{ . }} refers to the current item.
        """
        pattern = r'\{\{\s*range\s+\.Values\.([a-zA-Z0-9_.]+)\s*\}\}(.*?)\{\{\s*end\s*\}\}'

        def replacer(match: re.Match) -> str:
            path = match.group(1)
            body = match.group(2)
            items = self._resolve_path(path, values)
            if not items or not isinstance(items, list):
                return ""

            parts = []
            for item in items:
                # Replace {{ . }} with the current item
                rendered = re.sub(r'\{\{\s*\.\s*\}\}', str(item), body)
                parts.append(rendered)
            return "".join(parts)

        return re.sub(pattern, replacer, template, flags=re.DOTALL)

    def _process_conditionals(self, template: str, values: dict) -> str:
        """Process {{ if .Values.key }}...{{ else }}...{{ end }} blocks.

        A value is 'truthy' if it exists and is not None, False, 0, or "".
        """
        # Pattern with optional else
        pattern = (
            r'\{\{\s*if\s+\.Values\.([a-zA-Z0-9_.]+)\s*\}\}'
            r'(.*?)'
            r'(?:\{\{\s*else\s*\}\}(.*?))?'
            r'\{\{\s*end\s*\}\}'
        )

        def replacer(match: re.Match) -> str:
            path = match.group(1)
            true_block = match.group(2)
            false_block = match.group(3) or ""

            value = self._resolve_path(path, values)
            if value:
                return true_block
            return false_block

        return re.sub(pattern, replacer, template, flags=re.DOTALL)

    def _process_values(self, template: str, values: dict) -> str:
        """Process {{ .Values.key | pipe1 | pipe2 }} substitutions."""
        pattern = r'\{\{\s*\.Values\.([a-zA-Z0-9_.]+)((?:\s*\|\s*[a-zA-Z0-9_]+(?:\s+[^\|}]*)?)*)?\s*\}\}'

        def replacer(match: re.Match) -> str:
            path = match.group(1)
            pipes_str = match.group(2) or ""
            value = self._resolve_path(path, values)

            # Parse and apply pipe functions
            pipes = self._parse_pipes(pipes_str)
            result = self._apply_pipes(value, pipes)

            if result is None:
                return ""
            return str(result)

        return re.sub(pattern, replacer, template)

    def _parse_pipes(self, pipes_str: str) -> list[tuple[str, str]]:
        """Parse pipe chain like '| default "val" | quote' into tuples.

        Returns list of (function_name, argument) tuples.
        """
        pipes: list[tuple[str, str]] = []
        if not pipes_str.strip():
            return pipes

        # Split on pipe character
        segments = pipes_str.split("|")
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Extract function name and optional argument
            parts = segment.split(None, 1)
            func_name = parts[0]
            arg = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
            pipes.append((func_name, arg))

        return pipes

    def _apply_pipes(self, value: Any, pipes: list[tuple[str, str]]) -> Any:
        """Apply a chain of pipe functions to a value."""
        result = value
        for func_name, arg in pipes:
            if func_name == "default":
                if result is None or result == "" or result is False:
                    result = arg
            elif func_name == "quote":
                result = f'"{result}"' if result is not None else '""'
            elif func_name == "upper":
                result = str(result).upper() if result is not None else ""
            elif func_name == "lower":
                result = str(result).lower() if result is not None else ""
            elif func_name == "indent":
                indent_size = int(arg) if arg else 2
                if result is not None:
                    lines = str(result).split("\n")
                    indented = [" " * indent_size + line for line in lines]
                    result = "\n".join(indented)
                else:
                    result = ""
        return result
