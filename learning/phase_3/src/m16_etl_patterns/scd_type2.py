"""
Slowly Changing Dimension Type 2
===================================

SCD Type 2 is a technique for tracking the full history of changes
to dimension records over time.

HOW IT WORKS:
- Each dimension record has: valid_from, valid_to, is_current.
- When an attribute changes, the current record is "closed"
  (valid_to = now, is_current = False) and a new record is opened
  (valid_from = now, is_current = True).
- This preserves all historical versions.

SCD TYPES COMPARISON:
- Type 0: Don't update (retain original). Rarely used.
- Type 1: Overwrite the old value. No history preserved.
- Type 2: Add a new row with versioning. Full history preserved.
- Type 3: Add a new column (e.g., previous_address). Limited history.
- Type 6: Hybrid of 1+2+3. Current + history + previous.

USE CASE:
A driver changes their vehicle from "sedan" to "SUV". We need:
- Rides before the change → joined to "sedan" version.
- Rides after the change → joined to "SUV" version.
- SCD Type 2 enables this point-in-time join.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import copy


@dataclass
class SCDRecord:
    """A versioned dimension record with temporal tracking."""
    key: str
    attributes: dict[str, Any]
    valid_from: str  # ISO timestamp
    valid_to: str | None  # None means currently valid
    is_current: bool
    version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            **self.attributes,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "is_current": self.is_current,
            "version": self.version,
        }


class SCDType2Table:
    """
    Manages a dimension table with SCD Type 2 versioning.

    Every change creates a new version of the record while
    preserving the old version with temporal bounds.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._records: list[SCDRecord] = []

    @property
    def all_records(self) -> list[SCDRecord]:
        return list(self._records)

    @property
    def current_records(self) -> list[SCDRecord]:
        return [r for r in self._records if r.is_current]

    @property
    def total_records(self) -> int:
        return len(self._records)

    @property
    def unique_keys(self) -> int:
        return len(set(r.key for r in self._records))

    def insert(self, key: str, attributes: dict[str, Any], timestamp: str | None = None) -> SCDRecord:
        """
        Insert a new dimension record (first version).
        """
        ts = timestamp or datetime.now().isoformat()

        # Check if key already exists
        existing = self._get_current(key)
        if existing is not None:
            raise ValueError(f"Key '{key}' already exists. Use apply_change() to update.")

        record = SCDRecord(
            key=key,
            attributes=copy.deepcopy(attributes),
            valid_from=ts,
            valid_to=None,
            is_current=True,
            version=1,
        )
        self._records.append(record)
        return record

    def apply_change(
        self, key: str, new_attributes: dict[str, Any], timestamp: str | None = None
    ) -> tuple[SCDRecord, SCDRecord]:
        """
        Apply a change to a dimension record using SCD Type 2.

        1. Close the current record (set valid_to, is_current=False).
        2. Insert a new record (valid_from = now, is_current=True).

        Returns (closed_record, new_record).
        """
        ts = timestamp or datetime.now().isoformat()
        current = self._get_current(key)
        if current is None:
            raise KeyError(f"No current record for key '{key}'")

        # Close the current record
        current.valid_to = ts
        current.is_current = False

        # Merge old + new attributes
        merged = {**current.attributes, **new_attributes}

        # Create new version
        new_record = SCDRecord(
            key=key,
            attributes=merged,
            valid_from=ts,
            valid_to=None,
            is_current=True,
            version=current.version + 1,
        )
        self._records.append(new_record)
        return current, new_record

    def as_of(self, key: str, timestamp: str) -> SCDRecord | None:
        """
        Point-in-time lookup: find the version valid at a specific timestamp.

        This is the key feature of SCD Type 2. It enables joining
        fact records with the dimension version that was active
        at the time the fact event occurred.
        """
        for record in self._records:
            if record.key != key:
                continue
            if record.valid_from <= timestamp:
                if record.valid_to is None or timestamp < record.valid_to:
                    return record
        return None

    def history(self, key: str) -> list[SCDRecord]:
        """Get all versions of a record, ordered by version."""
        versions = [r for r in self._records if r.key == key]
        return sorted(versions, key=lambda r: r.version)

    def _get_current(self, key: str) -> SCDRecord | None:
        """Get the current version of a record."""
        for record in self._records:
            if record.key == key and record.is_current:
                return record
        return None

    def lookup(self, key: str) -> SCDRecord | None:
        """Look up the current version of a record."""
        return self._get_current(key)
