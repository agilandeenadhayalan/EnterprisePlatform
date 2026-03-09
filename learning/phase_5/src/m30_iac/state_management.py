"""
State Management — Terraform-style state tracking, locking, and drift detection.

WHY THIS MATTERS:
Terraform's state file is the source of truth for what infrastructure
exists. Without state:
  - Terraform wouldn't know what it has already created.
  - It couldn't compute diffs between desired and actual state.
  - Multiple engineers could create duplicate resources.

Key concepts:
  - State Store: maps resource IDs to their current properties and
    status (created/updated/deleted).
  - State Locking: prevents concurrent applies from corrupting state.
    In production, this uses DynamoDB (AWS) or GCS (GCP) locks.
  - Drift Detection: compares desired configuration to actual state
    to find resources that have been manually changed (drifted).
"""

import time
from uuid import uuid4


class ResourceState:
    """The recorded state of a single infrastructure resource.

    Each entry in the state file captures:
    - resource_id: the unique identifier (e.g. "aws_vpc.main")
    - properties: the current property values
    - status: created, updated, or deleted
    - last_modified: timestamp of the last state change
    """

    def __init__(self, resource_id: str, properties: dict, status: str, last_modified: float = None):
        self.resource_id = resource_id
        self.properties = properties
        self.status = status
        self.last_modified = last_modified or time.time()


class StateStore:
    """A key-value store for infrastructure state.

    Models Terraform's terraform.tfstate file. Each resource that
    Terraform manages has an entry with its current properties and
    lifecycle status.

    The store supports serialization (to_dict/from_dict) for
    persistence to disk, S3, or GCS.
    """

    def __init__(self):
        self._state: dict[str, ResourceState] = {}

    def get(self, resource_id: str) -> ResourceState:
        """Get the state for a resource, or None if not tracked."""
        return self._state.get(resource_id)

    def set(self, resource_id: str, properties: dict, status: str) -> None:
        """Set or update the state for a resource."""
        self._state[resource_id] = ResourceState(
            resource_id=resource_id,
            properties=properties,
            status=status,
        )

    def delete(self, resource_id: str) -> None:
        """Remove a resource from the state store."""
        if resource_id in self._state:
            del self._state[resource_id]

    def list_all(self) -> list:
        """List all resource states."""
        return list(self._state.values())

    def to_dict(self) -> dict:
        """Serialize the state store for persistence."""
        return {
            "resources": {
                rid: {
                    "resource_id": state.resource_id,
                    "properties": state.properties,
                    "status": state.status,
                    "last_modified": state.last_modified,
                }
                for rid, state in self._state.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StateStore":
        """Deserialize a state store from a dict.

        This is used when loading terraform.tfstate from disk.
        """
        store = cls()
        for rid, entry in data.get("resources", {}).items():
            store._state[rid] = ResourceState(
                resource_id=entry["resource_id"],
                properties=entry["properties"],
                status=entry["status"],
                last_modified=entry.get("last_modified", 0.0),
            )
        return store


class StateLock:
    """Prevents concurrent state modifications.

    In production, Terraform uses a distributed lock (DynamoDB, GCS,
    Consul) to ensure only one `terraform apply` runs at a time.
    Without locking, two engineers could apply conflicting changes
    simultaneously and corrupt the state file.

    Lock semantics:
    - acquire(lock_id, owner): take the lock. Fails if held by another.
    - release(lock_id, owner): release the lock. Fails if held by another.
    - Re-entrant: the same owner can acquire a lock they already hold.
    """

    def __init__(self):
        self._locks: dict[str, dict] = {}

    def acquire(self, lock_id: str, owner: str) -> bool:
        """Acquire a lock. Returns True if successful.

        If the lock is already held by the same owner, returns True
        (re-entrant). If held by a different owner, returns False.
        """
        if lock_id in self._locks:
            if self._locks[lock_id]["owner"] == owner:
                return True
            return False
        self._locks[lock_id] = {
            "owner": owner,
            "version": uuid4().hex[:8],
            "acquired_at": time.time(),
        }
        return True

    def release(self, lock_id: str, owner: str) -> bool:
        """Release a lock. Returns True if successful.

        Fails if the lock is held by a different owner, preventing
        accidental release of someone else's lock.
        """
        if lock_id not in self._locks:
            return True  # Already unlocked
        if self._locks[lock_id]["owner"] != owner:
            return False
        del self._locks[lock_id]
        return True

    def is_locked(self, lock_id: str) -> bool:
        """Check if a lock is currently held."""
        return lock_id in self._locks

    def get_lock_info(self, lock_id: str) -> dict:
        """Get information about a lock, or None if not locked."""
        return self._locks.get(lock_id)


class DriftResult:
    """The result of comparing desired vs actual state for one resource.

    drift_type indicates what kind of drift was detected:
    - "added": resource exists in desired but not actual (needs creation).
    - "removed": resource exists in actual but not desired (was deleted).
    - "modified": resource exists in both but properties differ.
    """

    def __init__(self, resource_id: str, drift_type: str, desired_value=None, actual_value=None):
        self.resource_id = resource_id
        self.drift_type = drift_type
        self.desired_value = desired_value
        self.actual_value = actual_value


class DriftDetector:
    """Detects configuration drift between desired and actual state.

    Drift happens when someone manually changes infrastructure outside
    of Terraform (e.g. editing a security group in the AWS console).
    Detecting drift is essential for maintaining infrastructure-as-code
    discipline.

    The detector compares two dicts of resource_id -> properties:
    - desired: what the Terraform configuration says should exist.
    - actual: what the cloud provider API reports actually exists.
    """

    def detect(self, desired: dict, actual: dict) -> list:
        """Compare desired and actual state to find drift.

        Args:
            desired: dict of resource_id -> properties (from config).
            actual: dict of resource_id -> properties (from cloud API).

        Returns:
            A list of DriftResult objects describing each difference.
        """
        results = []

        # Resources in desired but not actual → added
        for rid in desired:
            if rid not in actual:
                results.append(DriftResult(
                    resource_id=rid,
                    drift_type="added",
                    desired_value=desired[rid],
                    actual_value=None,
                ))

        # Resources in actual but not desired → removed
        for rid in actual:
            if rid not in desired:
                results.append(DriftResult(
                    resource_id=rid,
                    drift_type="removed",
                    desired_value=None,
                    actual_value=actual[rid],
                ))

        # Resources in both but with different properties → modified
        for rid in desired:
            if rid in actual and desired[rid] != actual[rid]:
                results.append(DriftResult(
                    resource_id=rid,
                    drift_type="modified",
                    desired_value=desired[rid],
                    actual_value=actual[rid],
                ))

        return results
