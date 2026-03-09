"""
Medallion Architecture (Bronze / Silver / Gold)
==================================================

The medallion architecture organizes data in a lake into three layers
of increasing quality and refinement:

1. **Bronze (Raw)** — Exact copy of source data. Append-only, immutable.
   No transformations. Preserves the original data for reprocessing.
   Think of it as the "audit trail."

2. **Silver (Cleaned)** — Validated, deduplicated, and standardized data.
   Nulls are handled, types are enforced, and business rules are applied.
   This is the "single source of truth" for analytics.

3. **Gold (Aggregated)** — Pre-computed business metrics and KPIs.
   Analytics-ready tables optimized for specific use cases.
   Dashboard queries hit Gold tables for instant results.

WHY medallion:
- Clear data lineage (raw -> cleaned -> aggregated).
- Reprocessable: if Silver logic changes, rerun from Bronze.
- Separation of concerns: ingestion, cleaning, and analytics are independent.
- Each layer has different access patterns and SLAs.

DATA FLOW:
    Source Systems -> Bronze (append raw) -> Silver (clean & dedupe)
                                          -> Gold (aggregate & serve)
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BronzeRecord:
    """An immutable record in the Bronze layer."""
    record_id: str
    source: str
    ingested_at: str
    raw_data: dict[str, Any]

    def fingerprint(self) -> str:
        """Content hash for deduplication in Silver."""
        content = str(sorted(self.raw_data.items()))
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class SilverRecord:
    """A cleaned and validated record in the Silver layer."""
    record_id: str
    source: str
    cleaned_at: str
    data: dict[str, Any]
    fingerprint: str


@dataclass
class GoldRecord:
    """An aggregated record in the Gold layer."""
    group_key: dict[str, Any]
    metrics: dict[str, float]
    computed_at: str
    record_count: int


class BronzeLayer:
    """
    Bronze layer: raw, unmodified data storage.

    Rules:
    - Append-only: never update or delete.
    - Store exactly what the source sent.
    - Add metadata: source, ingestion timestamp.
    - This is your insurance policy for reprocessing.
    """

    def __init__(self) -> None:
        self._records: list[BronzeRecord] = []
        self._next_id = 0

    @property
    def records(self) -> list[BronzeRecord]:
        return list(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    def ingest(
        self,
        raw_data: dict[str, Any] | list[dict[str, Any]],
        source: str,
        timestamp: str | None = None,
    ) -> list[BronzeRecord]:
        """
        Ingest raw data into the Bronze layer. No transformations.

        Args:
            raw_data: Single record or list of records.
            source: Name of the source system.
            timestamp: Ingestion timestamp (ISO format).
        """
        ts = timestamp or datetime.now().isoformat()
        items = raw_data if isinstance(raw_data, list) else [raw_data]
        ingested = []
        for item in items:
            self._next_id += 1
            record = BronzeRecord(
                record_id=f"bronze-{self._next_id}",
                source=source,
                ingested_at=ts,
                raw_data=copy.deepcopy(item),
            )
            self._records.append(record)
            ingested.append(record)
        return ingested


class SilverLayer:
    """
    Silver layer: cleaned, validated, and deduplicated data.

    Transformations applied:
    1. Remove records with null required fields.
    2. Standardize data types (e.g., string numbers to floats).
    3. Deduplicate by content fingerprint.
    4. Validate value ranges and business rules.
    """

    def __init__(self, required_fields: list[str] | None = None) -> None:
        self._records: list[SilverRecord] = []
        self._seen_fingerprints: set[str] = set()
        self._rejected_count = 0
        self._dedup_count = 0
        self.required_fields = required_fields or []

    @property
    def records(self) -> list[SilverRecord]:
        return list(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def rejected_count(self) -> int:
        return self._rejected_count

    @property
    def dedup_count(self) -> int:
        return self._dedup_count

    def transform(
        self,
        bronze_records: list[BronzeRecord],
        type_conversions: dict[str, type] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
    ) -> list[SilverRecord]:
        """
        Transform Bronze records into Silver records.

        Steps:
        1. Check required fields (reject if missing/null).
        2. Apply type conversions.
        3. Validate value ranges.
        4. Deduplicate by content fingerprint.
        """
        conversions = type_conversions or {}
        ranges = value_ranges or {}
        accepted = []

        for bronze in bronze_records:
            data = copy.deepcopy(bronze.raw_data)

            # Step 1: Check required fields
            if not self._check_required(data):
                self._rejected_count += 1
                continue

            # Step 2: Type conversions
            try:
                for field_name, target_type in conversions.items():
                    if field_name in data and data[field_name] is not None:
                        data[field_name] = target_type(data[field_name])
            except (ValueError, TypeError):
                self._rejected_count += 1
                continue

            # Step 3: Value range validation
            if not self._check_ranges(data, ranges):
                self._rejected_count += 1
                continue

            # Step 4: Deduplicate
            fp = bronze.fingerprint()
            if fp in self._seen_fingerprints:
                self._dedup_count += 1
                continue
            self._seen_fingerprints.add(fp)

            record = SilverRecord(
                record_id=bronze.record_id.replace("bronze", "silver"),
                source=bronze.source,
                cleaned_at=datetime.now().isoformat(),
                data=data,
                fingerprint=fp,
            )
            self._records.append(record)
            accepted.append(record)

        return accepted

    def _check_required(self, data: dict[str, Any]) -> bool:
        """Check that all required fields are present and non-null."""
        for field_name in self.required_fields:
            if field_name not in data or data[field_name] is None:
                return False
        return True

    def _check_ranges(
        self, data: dict[str, Any], ranges: dict[str, tuple[float, float]]
    ) -> bool:
        """Check that numeric fields are within expected ranges."""
        for field_name, (low, high) in ranges.items():
            if field_name in data and data[field_name] is not None:
                try:
                    val = float(data[field_name])
                    if not (low <= val <= high):
                        return False
                except (ValueError, TypeError):
                    return False
        return True


class GoldLayer:
    """
    Gold layer: pre-computed aggregations for analytics.

    Takes Silver records and produces aggregated metrics
    grouped by business dimensions (zone, date, driver, etc.).
    """

    def __init__(self) -> None:
        self._records: list[GoldRecord] = []

    @property
    def records(self) -> list[GoldRecord]:
        return list(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    def aggregate(
        self,
        silver_records: list[SilverRecord],
        group_by: list[str],
        metrics: dict[str, str],  # field -> agg_function (sum, avg, count, min, max)
    ) -> list[GoldRecord]:
        """
        Aggregate Silver records into Gold records.

        Args:
            silver_records: Records to aggregate.
            group_by: Fields to group by.
            metrics: Mapping of field -> aggregation function.
        """
        groups: dict[tuple, list[dict[str, Any]]] = {}
        for record in silver_records:
            key = tuple(record.data.get(col) for col in group_by)
            groups.setdefault(key, []).append(record.data)

        results = []
        for key, rows in groups.items():
            group_key = {col: val for col, val in zip(group_by, key)}
            computed_metrics: dict[str, float] = {}

            for metric_field, func in metrics.items():
                values = [
                    r[metric_field] for r in rows
                    if metric_field in r and r[metric_field] is not None
                ]
                if not values:
                    computed_metrics[metric_field] = 0.0
                    continue

                if func == "sum":
                    computed_metrics[metric_field] = sum(values)
                elif func == "avg":
                    computed_metrics[metric_field] = round(sum(values) / len(values), 4)
                elif func == "count":
                    computed_metrics[metric_field] = float(len(values))
                elif func == "min":
                    computed_metrics[metric_field] = min(values)
                elif func == "max":
                    computed_metrics[metric_field] = max(values)

            gold_record = GoldRecord(
                group_key=group_key,
                metrics=computed_metrics,
                computed_at=datetime.now().isoformat(),
                record_count=len(rows),
            )
            self._records.append(gold_record)
            results.append(gold_record)

        return results


class MedallionPipeline:
    """
    Orchestrates the full Bronze -> Silver -> Gold flow.

    Convenience class that wires together the three layers
    and runs the complete pipeline in one call.
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        type_conversions: dict[str, type] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
        group_by: list[str] | None = None,
        metrics: dict[str, str] | None = None,
    ) -> None:
        self.bronze = BronzeLayer()
        self.silver = SilverLayer(required_fields=required_fields)
        self.gold = GoldLayer()
        self._type_conversions = type_conversions or {}
        self._value_ranges = value_ranges or {}
        self._group_by = group_by or []
        self._metrics = metrics or {}

    def run(
        self, raw_data: list[dict[str, Any]], source: str = "api"
    ) -> dict[str, int]:
        """
        Run the full pipeline: ingest -> clean -> aggregate.

        Returns stats about each layer.
        """
        # Bronze: ingest raw
        bronze_records = self.bronze.ingest(raw_data, source=source)

        # Silver: clean and validate
        silver_records = self.silver.transform(
            bronze_records,
            type_conversions=self._type_conversions,
            value_ranges=self._value_ranges,
        )

        # Gold: aggregate (only if group_by is configured)
        gold_records = []
        if self._group_by and self._metrics:
            gold_records = self.gold.aggregate(
                silver_records,
                group_by=self._group_by,
                metrics=self._metrics,
            )

        return {
            "bronze_ingested": len(bronze_records),
            "silver_accepted": len(silver_records),
            "silver_rejected": self.silver.rejected_count,
            "silver_deduped": self.silver.dedup_count,
            "gold_groups": len(gold_records),
        }
