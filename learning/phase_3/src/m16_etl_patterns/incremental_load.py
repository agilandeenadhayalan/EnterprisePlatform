"""
Incremental Loading with Watermarks
======================================

Incremental loading extracts only new or changed data since the
last successful run, rather than re-extracting everything.

KEY CONCEPTS:

1. **Watermark** — A bookmark (usually a timestamp or ID) that records
   "how far we've gotten." The next run starts from this point.

2. **High Watermark** — The maximum value of the watermark column
   in the last successful batch. Next extraction: WHERE updated_at > watermark.

3. **Full vs Incremental**:
   - Full load: Extract all data every time. Simple but slow.
   - Incremental: Extract only changes. Fast but requires watermark tracking.

WHY incremental:
- Processes 1000 rows instead of 10 million on each run.
- Reduces load on source systems.
- Faster pipeline execution (minutes vs hours).
- Less network and compute cost.

RISKS:
- Missed updates if watermark is advanced before commit.
- Late-arriving data can be missed.
- Schema changes require careful handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import copy


class WatermarkStore:
    """
    Persists watermark values between pipeline runs.

    In production, watermarks would be stored in a database, file,
    or configuration management system. This simulation uses memory.

    Best practice: Only advance the watermark AFTER the data has been
    successfully loaded to the destination. Otherwise, a crash would
    lose the data between the old and new watermark.
    """

    def __init__(self) -> None:
        self._watermarks: dict[str, Any] = {}

    def get(self, source: str) -> Any:
        """Get the current watermark for a source. Returns None if first run."""
        return self._watermarks.get(source)

    def set(self, source: str, value: Any) -> None:
        """Update the watermark for a source."""
        self._watermarks[source] = value

    def all_watermarks(self) -> dict[str, Any]:
        """Get all stored watermarks."""
        return dict(self._watermarks)


@dataclass
class LoadResult:
    """Result of an incremental load operation."""
    source: str
    records_extracted: int
    records_loaded: int
    old_watermark: Any
    new_watermark: Any
    is_full_load: bool


class IncrementalLoader:
    """
    Watermark-based incremental data loader.

    Tracks a high watermark per source and extracts only records
    newer than the watermark. The watermark is advanced only after
    successful loading.
    """

    def __init__(
        self,
        watermark_store: WatermarkStore,
        watermark_column: str = "updated_at",
    ) -> None:
        self.store = watermark_store
        self.watermark_column = watermark_column
        self._load_history: list[LoadResult] = []

    @property
    def load_history(self) -> list[LoadResult]:
        return list(self._load_history)

    def extract_new(
        self,
        source: str,
        all_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract records newer than the watermark.

        If no watermark exists (first run), extract everything.
        """
        watermark = self.store.get(source)

        if watermark is None:
            # First run — full extraction
            return [dict(r) for r in all_records]

        # Incremental — only records after the watermark
        return [
            dict(r) for r in all_records
            if r.get(self.watermark_column) is not None
            and r[self.watermark_column] > watermark
        ]

    def load(
        self,
        source: str,
        all_records: list[dict[str, Any]],
        destination: list[dict[str, Any]],
    ) -> LoadResult:
        """
        Extract new records and load them to the destination.

        Only advances the watermark after successful loading.
        """
        old_watermark = self.store.get(source)
        is_full = old_watermark is None

        new_records = self.extract_new(source, all_records)

        if not new_records:
            result = LoadResult(
                source=source,
                records_extracted=0,
                records_loaded=0,
                old_watermark=old_watermark,
                new_watermark=old_watermark,
                is_full_load=is_full,
            )
            self._load_history.append(result)
            return result

        # Load to destination
        destination.extend(new_records)

        # Advance watermark to the max value in the extracted batch
        watermark_values = [
            r[self.watermark_column]
            for r in new_records
            if r.get(self.watermark_column) is not None
        ]
        new_watermark = max(watermark_values) if watermark_values else old_watermark
        self.store.set(source, new_watermark)

        result = LoadResult(
            source=source,
            records_extracted=len(new_records),
            records_loaded=len(new_records),
            old_watermark=old_watermark,
            new_watermark=new_watermark,
            is_full_load=is_full,
        )
        self._load_history.append(result)
        return result

    def load_with_failure_handling(
        self,
        source: str,
        all_records: list[dict[str, Any]],
        destination: list[dict[str, Any]],
        simulate_failure: bool = False,
    ) -> LoadResult:
        """
        Load with failure handling — don't advance watermark on failure.

        If loading fails, the watermark stays at the old value so the
        next run will re-extract the same records (at-least-once semantics).
        """
        old_watermark = self.store.get(source)
        is_full = old_watermark is None
        new_records = self.extract_new(source, all_records)

        if simulate_failure:
            # Don't advance watermark — next run will retry
            result = LoadResult(
                source=source,
                records_extracted=len(new_records),
                records_loaded=0,
                old_watermark=old_watermark,
                new_watermark=old_watermark,
                is_full_load=is_full,
            )
            self._load_history.append(result)
            return result

        return self.load(source, all_records, destination)
