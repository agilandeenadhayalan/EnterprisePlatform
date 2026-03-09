"""
Kustomize Overlay — patch-based configuration management without templates.

WHY THIS MATTERS:
While Helm uses templates (generate YAML from parameters), Kustomize uses
overlays (patch existing YAML). This is "configuration as data" rather
than "configuration as code". Kustomize is built into kubectl (kubectl
apply -k) and is the preferred approach for teams that find templates
too complex.

Two patching strategies:
  1. Strategic Merge Patch (SMP): deep-merges a partial resource into
     the base. Setting a value to None deletes that key.
  2. JSON Patch (RFC 6902): a sequence of precise operations (add,
     remove, replace, move, copy, test) using JSON Pointer paths.

Kustomize applies patches in order, building up the final manifest
layer by layer: base -> dev overlay -> team-specific patches.
"""

import copy
from typing import Any


class StrategicMergePatch:
    """Strategic Merge Patch — Kubernetes-native deep merge.

    In SMP, the patch is a partial resource spec that is deep-merged
    into the base. Keys present in the patch override the base. Keys
    set to None are *deleted* from the base. Keys absent from the patch
    are left unchanged.

    This is the most common patching strategy in Kubernetes because it
    mirrors how you think about changes: "I want to change X and delete
    Y, leave everything else alone."
    """

    def apply(self, base: dict, patch: dict) -> dict:
        """Apply a strategic merge patch to a base document.

        Rules:
          - dict + dict: merge recursively
          - None value: delete the key from result
          - Any other value: replace base value
          - Keys only in base: preserved
          - Keys only in patch: added

        Neither input dict is mutated.
        """
        result = copy.deepcopy(base)

        for key, value in patch.items():
            if value is None:
                # None means "delete this key"
                result.pop(key, None)
            elif (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.apply(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result


class JsonPatch:
    """JSON Patch (RFC 6902) — precise document mutation operations.

    Each operation is a dict with:
      - "op": one of "add", "remove", "replace", "move", "copy", "test"
      - "path": JSON Pointer (e.g. "/metadata/labels/app")
      - "value": the value (for add, replace, test)
      - "from": source path (for move, copy)

    JSON Pointer paths use '/' as separator. The root is "".
    Array indices are numeric (e.g. "/items/0").

    WHY JSON PATCH:
    While SMP is simpler, JSON Patch is more precise and can express
    operations that SMP cannot, like moving a value from one key to
    another, or testing a value before modifying it (atomic check-and-set).
    """

    def apply(self, document: dict, operations: list[dict]) -> dict:
        """Apply a list of JSON Patch operations to a document.

        Operations are applied in order. The document is not mutated.

        Raises:
            ValueError: For unsupported operations or path errors.
            KeyError: When test operation fails.
        """
        result = copy.deepcopy(document)

        for op in operations:
            op_type = op["op"]
            path = op.get("path", "")

            if op_type == "add":
                result = self._set_path(result, path, copy.deepcopy(op["value"]))
            elif op_type == "remove":
                result = self._remove_path(result, path)
            elif op_type == "replace":
                # Verify path exists, then set
                self._get_path(result, path)  # raises if missing
                result = self._set_path(result, path, copy.deepcopy(op["value"]))
            elif op_type == "move":
                value = self._get_path(result, op["from"])
                result = self._remove_path(result, op["from"])
                result = self._set_path(result, path, value)
            elif op_type == "copy":
                value = self._get_path(result, op["from"])
                result = self._set_path(result, path, copy.deepcopy(value))
            elif op_type == "test":
                actual = self._get_path(result, path)
                if actual != op["value"]:
                    raise KeyError(
                        f"Test failed at '{path}': expected {op['value']!r}, "
                        f"got {actual!r}"
                    )
            else:
                raise ValueError(f"Unsupported JSON Patch operation: '{op_type}'")

        return result

    def _parse_pointer(self, path: str) -> list[str]:
        """Parse a JSON Pointer path into segments.

        "/a/b/c" -> ["a", "b", "c"]
        "" -> []
        """
        if not path:
            return []
        if not path.startswith("/"):
            raise ValueError(f"JSON Pointer must start with '/', got '{path}'")
        parts = path[1:].split("/")
        # Unescape ~1 -> / and ~0 -> ~
        return [p.replace("~1", "/").replace("~0", "~") for p in parts]

    def _get_path(self, doc: Any, path: str) -> Any:
        """Navigate to a JSON Pointer path and return the value."""
        segments = self._parse_pointer(path)
        current = doc
        for seg in segments:
            if isinstance(current, dict):
                if seg not in current:
                    raise KeyError(f"Path segment '{seg}' not found")
                current = current[seg]
            elif isinstance(current, list):
                idx = int(seg)
                current = current[idx]
            else:
                raise KeyError(f"Cannot navigate into {type(current)} with '{seg}'")
        return current

    def _set_path(self, doc: dict, path: str, value: Any) -> dict:
        """Set a value at the given JSON Pointer path."""
        segments = self._parse_pointer(path)
        if not segments:
            if isinstance(value, dict):
                return value
            raise ValueError("Cannot replace root with non-dict value")

        result = copy.deepcopy(doc)
        current = result
        for seg in segments[:-1]:
            if isinstance(current, dict):
                if seg not in current:
                    current[seg] = {}
                current = current[seg]
            elif isinstance(current, list):
                current = current[int(seg)]

        last = segments[-1]
        if isinstance(current, dict):
            current[last] = value
        elif isinstance(current, list):
            idx = int(last)
            if idx == len(current):
                current.append(value)
            else:
                current[idx] = value

        return result

    def _remove_path(self, doc: dict, path: str) -> dict:
        """Remove the value at the given JSON Pointer path."""
        segments = self._parse_pointer(path)
        if not segments:
            raise ValueError("Cannot remove root document")

        result = copy.deepcopy(doc)
        current = result
        for seg in segments[:-1]:
            if isinstance(current, dict):
                current = current[seg]
            elif isinstance(current, list):
                current = current[int(seg)]

        last = segments[-1]
        if isinstance(current, dict):
            del current[last]
        elif isinstance(current, list):
            del current[int(last)]

        return result


class KustomizeOverlay:
    """Applies a sequence of patches to a base resource.

    In Kustomize, you start with a base resource (e.g. a Deployment YAML)
    and apply overlays for each environment. Each overlay contains patches
    that modify the base.

    The build process:
      1. Start with the base document.
      2. Apply each patch in order.
      3. The result is the final manifest ready for kubectl apply.

    Patches can be StrategicMergePatch or JsonPatch objects, as long as
    they have an `apply(base, patch_data)` method.
    """

    def __init__(self, base: dict, patches: list[tuple[Any, Any]] | None = None):
        """
        Args:
            base: The base Kubernetes resource document.
            patches: List of (patcher, patch_data) tuples. Each patcher
                     must have an apply(base, patch_data) method.
        """
        self.base = base
        self.patches = patches or []

    def add_patch(self, patcher: Any, patch_data: Any) -> None:
        """Add a patch to be applied during build.

        Args:
            patcher: An object with an apply() method (SMP or JsonPatch).
            patch_data: The patch data to pass to the patcher.
        """
        self.patches.append((patcher, patch_data))

    def build(self) -> dict:
        """Apply all patches in order and return the final document."""
        result = copy.deepcopy(self.base)
        for patcher, patch_data in self.patches:
            result = patcher.apply(result, patch_data)
        return result
