"""
Values Hierarchy & Semantic Versioning — Helm values merge order and chart versioning.

WHY THIS MATTERS:
Helm charts have a well-defined values precedence order:
  1. Chart's values.yaml (defaults)
  2. Parent chart's values (for sub-charts)
  3. User-supplied values file (-f custom-values.yaml)
  4. CLI --set flags (highest priority)

Each level can override the previous, and the merge is *deep*: nested
keys are merged recursively rather than replaced wholesale. This allows
you to override just "replicas: 5" without having to re-specify the
entire deployment configuration.

Semantic Versioning (SemVer) is used to version both Helm charts and
container images. Understanding SemVer is essential for dependency
management and safe upgrades.
"""

import copy
from functools import total_ordering


class ValuesHierarchy:
    """Deep-merge values with Helm's precedence order.

    In Helm, values from multiple sources are merged in a specific order.
    Later sources override earlier ones. The merge is deep: nested
    dictionaries are merged recursively, but non-dict values are replaced.

    Example:
        base  = {"a": {"x": 1, "y": 2}, "b": 3}
        over  = {"a": {"y": 9, "z": 4}}
        merge = {"a": {"x": 1, "y": 9, "z": 4}, "b": 3}
    """

    def merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries. Override wins on conflicts.

        For nested dicts, keys are merged recursively. For all other
        types, the override value replaces the base value entirely.

        Neither input dict is mutated.
        """
        result = copy.deepcopy(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def resolve(
        self,
        chart_defaults: dict,
        parent_values: dict,
        user_values: dict,
        cli_sets: dict,
    ) -> dict:
        """Resolve the final values by merging all sources in order.

        Precedence (lowest to highest):
          chart_defaults < parent_values < user_values < cli_sets

        This mirrors 'helm install -f user.yaml --set key=val'.
        """
        result = self.merge(chart_defaults, parent_values)
        result = self.merge(result, user_values)
        result = self.merge(result, cli_sets)
        return result


@total_ordering
class SemVer:
    """Semantic Versioning — MAJOR.MINOR.PATCH.

    SemVer rules:
      - MAJOR: Incompatible API changes
      - MINOR: Backwards-compatible new features
      - PATCH: Backwards-compatible bug fixes

    Comparison uses (major, minor, patch) tuple ordering:
      1.2.3 < 1.2.4 < 1.3.0 < 2.0.0

    WHY SEMVER:
    SemVer tells consumers what to expect from a version bump:
      - Patch bump: safe to auto-update
      - Minor bump: new features, existing code still works
      - Major bump: review required, may need code changes
    """

    def __init__(self, major: int, minor: int, patch: int):
        if major < 0 or minor < 0 or patch < 0:
            raise ValueError("Version components must be non-negative")
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, version_str: str) -> "SemVer":
        """Parse a version string like '1.2.3' into a SemVer object.

        Strips leading 'v' if present (e.g. 'v1.2.3' -> 1.2.3).
        """
        version_str = version_str.lstrip("v")
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid SemVer string '{version_str}', expected MAJOR.MINOR.PATCH"
            )
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def bump_major(self) -> "SemVer":
        """Bump the major version, resetting minor and patch to 0."""
        return SemVer(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemVer":
        """Bump the minor version, resetting patch to 0."""
        return SemVer(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemVer":
        """Bump the patch version."""
        return SemVer(self.major, self.minor, self.patch + 1)

    def _as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._as_tuple() == other._as_tuple()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._as_tuple() < other._as_tuple()

    def __hash__(self) -> int:
        return hash(self._as_tuple())

    def __repr__(self) -> str:
        return f"SemVer({self.major}.{self.minor}.{self.patch})"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
