"""
Data catalog and schema registry — organizing and versioning datasets.

WHY THIS MATTERS:
A growing platform accumulates hundreds of datasets. Without a catalog,
engineers waste hours asking "where is the trip data?" or "what does
the 'status' column mean?" A data catalog is the single source of truth
for discovering, understanding, and governing datasets.

Schema versioning prevents breaking changes: before modifying a table
schema, you check compatibility to ensure existing consumers won't break.

Key concepts:
  - Classification: public, internal, confidential, restricted
  - Searchability: find datasets by name, description, or tags
  - Schema compatibility: backward, forward, and full compatibility modes
  - Version history: track schema evolution over time
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DataClassification(Enum):
    """Data sensitivity classification levels.

    Determines access controls and handling requirements:
    - PUBLIC: can be shared externally
    - INTERNAL: company-wide access
    - CONFIDENTIAL: need-to-know access
    - RESTRICTED: maximum protection (PII, financial)
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class CatalogEntry:
    """A dataset registered in the data catalog.

    Captures metadata needed to discover, understand, and govern
    a dataset: who owns it, how sensitive it is, what it contains.
    """

    id: str
    name: str
    description: str
    owner: str
    classification: DataClassification
    schema: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class DataCatalog:
    """Searchable registry of datasets with classification and ownership.

    Provides CRUD operations and search capabilities for dataset
    metadata. Serves as the platform's "data yellow pages."
    """

    def __init__(self):
        self._entries: dict = {}

    def register(self, entry: CatalogEntry) -> None:
        """Add a dataset to the catalog."""
        self._entries[entry.id] = entry

    def get(self, entry_id: str) -> CatalogEntry:
        """Retrieve a catalog entry by ID. Returns None if not found."""
        return self._entries.get(entry_id)

    def search(self, query: str) -> list:
        """Search catalog by name, description, or tags.

        Case-insensitive substring matching against name, description,
        and tag values. Returns list of matching CatalogEntry objects.
        """
        query_lower = query.lower()
        results = []
        for entry in self._entries.values():
            if (
                query_lower in entry.name.lower()
                or query_lower in entry.description.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)
        return results

    def classify(self, entry_id: str, classification: DataClassification) -> None:
        """Update the classification level for a dataset.

        Raises KeyError if the entry doesn't exist.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            raise KeyError(f"Entry {entry_id} not found")
        entry.classification = classification
        entry.updated_at = datetime.utcnow()

    def by_owner(self, owner: str) -> list:
        """Filter catalog entries by owner.

        Returns list of CatalogEntry objects owned by the specified owner.
        """
        return [e for e in self._entries.values() if e.owner == owner]

    def by_classification(self, level: DataClassification) -> list:
        """Filter catalog entries by classification level.

        Returns list of CatalogEntry objects with the specified classification.
        """
        return [e for e in self._entries.values() if e.classification == level]


@dataclass
class SchemaVersion:
    """A versioned schema definition.

    Tracks schema evolution with compatibility checking against
    other versions.
    """

    version: int
    schema: dict  # field_name -> field_type mapping
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_compatible_with(self, other: "SchemaVersion") -> bool:
        """Check basic compatibility with another schema version.

        Two schemas are compatible if they share at least one common field.
        This is a simplified check — real compatibility is more nuanced.
        """
        my_fields = set(self.schema.keys())
        other_fields = set(other.schema.keys())
        return len(my_fields & other_fields) > 0


class SchemaRegistry:
    """Version-controlled schema registry with compatibility checking.

    Tracks schema versions for named datasets and checks whether
    proposed changes are backward/forward/fully compatible.
    """

    def __init__(self):
        self._schemas: dict = {}  # name -> list of SchemaVersion

    def register_schema(self, name: str, schema: dict) -> SchemaVersion:
        """Register a new schema version for a dataset.

        Auto-increments the version number. First registration is v1.
        """
        if name not in self._schemas:
            self._schemas[name] = []

        version = len(self._schemas[name]) + 1
        sv = SchemaVersion(version=version, schema=schema)
        self._schemas[name].append(sv)
        return sv

    def get_latest(self, name: str) -> SchemaVersion:
        """Get the latest schema version for a dataset.

        Returns None if the dataset has no registered schemas.
        """
        versions = self._schemas.get(name, [])
        if not versions:
            return None
        return versions[-1]

    def check_compatibility(self, name: str, new_schema: dict, mode: str = "backward") -> bool:
        """Check if a new schema is compatible with the latest version.

        Modes:
          - backward: new schema can read old data.
            Allowed: add optional fields. Forbidden: remove existing fields.
          - forward: old schema can read new data.
            Allowed: remove optional fields. Forbidden: add new required fields.
          - full: both backward and forward compatible.

        Returns True if compatible, False otherwise.
        Returns True if no existing schema (first version is always compatible).
        """
        latest = self.get_latest(name)
        if latest is None:
            return True

        old_fields = set(latest.schema.keys())
        new_fields = set(new_schema.keys())

        if mode == "backward":
            # All old fields must still exist in new schema
            removed = old_fields - new_fields
            return len(removed) == 0

        elif mode == "forward":
            # No new required fields added (new fields not in old)
            added = new_fields - old_fields
            return len(added) == 0

        elif mode == "full":
            # Both directions must be compatible
            return old_fields == new_fields

        return False

    def get_history(self, name: str) -> list:
        """Get all schema versions for a dataset.

        Returns list of SchemaVersion in chronological order.
        """
        return list(self._schemas.get(name, []))
