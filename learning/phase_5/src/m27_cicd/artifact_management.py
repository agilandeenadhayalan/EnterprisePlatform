"""
Artifact Management — versioned build artifact registry.

WHY THIS MATTERS:
CI/CD pipelines produce build artifacts (container images, binaries,
packages) that must be stored, versioned, and retrieved reliably. An
artifact registry provides:

  - Immutable storage: once published, an artifact version cannot change.
  - Version ordering: SemVer-based ordering for finding latest versions.
  - Integrity verification: checksums ensure artifacts are not tampered with.
  - Lifecycle management: old versions can be pruned to save storage.

In practice, this maps to Docker registries (Harbor, ECR, GCR), package
registries (npm, PyPI, Maven), or generic artifact stores (Artifactory).
"""

from datetime import datetime


class Artifact:
    """A versioned build artifact with metadata and integrity checksum.

    Attributes:
        name: Artifact name (e.g. "mobility-api").
        version: SemVer version string (e.g. "1.2.3").
        build_metadata: Dict of build info (commit, branch, builder, etc).
        checksum: SHA256 hash of the artifact contents.
        created_at: Timestamp when the artifact was built.
    """

    def __init__(
        self,
        name: str,
        version: str,
        build_metadata: dict | None = None,
        checksum: str = "",
        created_at: datetime | None = None,
    ):
        self.name = name
        self.version = version
        self.build_metadata = build_metadata or {}
        self.checksum = checksum
        self.created_at = created_at or datetime.now()

    def _version_tuple(self) -> tuple[int, ...]:
        """Parse version string to tuple for comparison."""
        clean = self.version.lstrip("v")
        return tuple(int(p) for p in clean.split("."))

    def __repr__(self) -> str:
        return f"Artifact('{self.name}:{self.version}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Artifact):
            return NotImplemented
        return self.name == other.name and self.version == other.version


class ArtifactRegistry:
    """Registry for storing and retrieving versioned artifacts.

    The registry organizes artifacts by name. Each name can have multiple
    versions. Version ordering follows SemVer semantics.

    WHY A REGISTRY:
    Without a registry, teams resort to storing artifacts in shared
    filesystems or S3 buckets with ad-hoc naming conventions. This leads
    to "which version is deployed?" confusion, missing artifacts, and
    no integrity verification.
    """

    def __init__(self):
        self._artifacts: dict[str, list[Artifact]] = {}

    def publish(self, artifact: Artifact) -> None:
        """Publish an artifact to the registry.

        Raises:
            ValueError: If this exact version already exists.
        """
        name = artifact.name
        if name not in self._artifacts:
            self._artifacts[name] = []

        # Check for duplicate version
        for existing in self._artifacts[name]:
            if existing.version == artifact.version:
                raise ValueError(
                    f"Artifact '{name}:{artifact.version}' already exists"
                )

        self._artifacts[name].append(artifact)

    def get(self, name: str, version: str | None = None) -> Artifact:
        """Get an artifact by name and optional version.

        If version is None, returns the latest version.

        Raises:
            KeyError: If artifact or version not found.
        """
        if name not in self._artifacts or not self._artifacts[name]:
            raise KeyError(f"Artifact '{name}' not found")

        if version is None:
            return self.get_latest(name)

        for artifact in self._artifacts[name]:
            if artifact.version == version:
                return artifact

        raise KeyError(f"Artifact '{name}:{version}' not found")

    def get_latest(self, name: str) -> Artifact:
        """Get the latest version of an artifact by SemVer ordering.

        Raises:
            KeyError: If artifact not found.
        """
        if name not in self._artifacts or not self._artifacts[name]:
            raise KeyError(f"Artifact '{name}' not found")

        return max(self._artifacts[name], key=lambda a: a._version_tuple())

    def list(self, name: str) -> list[Artifact]:
        """List all versions of an artifact, sorted by version ascending.

        Raises:
            KeyError: If artifact not found.
        """
        if name not in self._artifacts:
            raise KeyError(f"Artifact '{name}' not found")

        return sorted(self._artifacts[name], key=lambda a: a._version_tuple())

    def delete(self, name: str, version: str) -> None:
        """Delete a specific version of an artifact.

        Raises:
            KeyError: If artifact or version not found.
        """
        if name not in self._artifacts:
            raise KeyError(f"Artifact '{name}' not found")

        for i, artifact in enumerate(self._artifacts[name]):
            if artifact.version == version:
                self._artifacts[name].pop(i)
                return

        raise KeyError(f"Artifact '{name}:{version}' not found")
