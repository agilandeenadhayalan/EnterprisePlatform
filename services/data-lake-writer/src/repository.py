"""
Data Lake Writer repository — in-memory storage simulating MinIO buckets.

Each Medallion layer (bronze, silver, gold) is represented as a list of records
stored in a dictionary. In production, this would interact with MinIO/S3.
"""

import json
import sys
import uuid
from datetime import datetime
from typing import Any, Optional

from models import MedallionRecord, TransformJob, LayerStats


class DataLakeRepository:
    """In-memory data lake storage simulating MinIO buckets."""

    def __init__(self):
        # layer_name -> list of MedallionRecord
        self._layers: dict[str, list[MedallionRecord]] = {
            "bronze": [],
            "silver": [],
            "gold": [],
        }
        self._transform_jobs: dict[str, TransformJob] = {}

    def write_record(
        self,
        layer: str,
        source: str,
        data: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> MedallionRecord:
        """Write a record to a specific layer."""
        if layer not in self._layers:
            raise ValueError(f"Invalid layer: {layer}. Must be one of: bronze, silver, gold")

        record = MedallionRecord(
            record_id=str(uuid.uuid4()),
            layer=layer,
            source=source,
            data=data,
            metadata=metadata,
        )
        self._layers[layer].append(record)
        return record

    def get_layer_records(self, layer: str) -> list[MedallionRecord]:
        """Get all records in a layer."""
        if layer not in self._layers:
            raise ValueError(f"Invalid layer: {layer}")
        return self._layers[layer]

    def get_layer_stats(self, layer: str) -> LayerStats:
        """Get statistics for a specific layer."""
        if layer not in self._layers:
            raise ValueError(f"Invalid layer: {layer}")

        records = self._layers[layer]
        total_size = sum(
            sys.getsizeof(json.dumps(r.data)) for r in records
        )
        return LayerStats(
            layer=layer,
            object_count=len(records),
            total_size_bytes=total_size,
        )

    def get_all_layer_stats(self) -> list[LayerStats]:
        """Get statistics for all layers."""
        return [self.get_layer_stats(layer) for layer in self._layers]

    def transform_bronze_to_silver(
        self,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TransformJob:
        """
        Transform Bronze raw data to Silver cleaned format.

        Silver cleaning:
        - Remove null values from data
        - Ensure consistent types (stringify values)
        - Deduplicate by source + data hash
        """
        job_id = str(uuid.uuid4())
        job = TransformJob(
            job_id=job_id,
            source_layer="bronze",
            target_layer="silver",
            status="running",
        )

        bronze_records = self._layers["bronze"]
        if source_filter:
            bronze_records = [r for r in bronze_records if r.source == source_filter]
        if limit:
            bronze_records = bronze_records[:limit]

        job.records_in = len(bronze_records)

        # Dedup tracking by content hash
        seen_hashes: set[str] = set()
        records_out = 0

        for record in bronze_records:
            # Clean: remove null values
            cleaned_data = {k: v for k, v in record.data.items() if v is not None}

            # Clean: ensure string types for consistency
            for key, value in cleaned_data.items():
                if not isinstance(value, (str, int, float, bool, list, dict)):
                    cleaned_data[key] = str(value)

            # Dedup: hash the cleaned data
            data_hash = hash(json.dumps(cleaned_data, sort_keys=True))
            content_key = f"{record.source}:{data_hash}"
            if content_key in seen_hashes:
                continue
            seen_hashes.add(content_key)

            # Write to silver
            silver_record = MedallionRecord(
                record_id=str(uuid.uuid4()),
                layer="silver",
                source=record.source,
                data=cleaned_data,
                metadata={
                    **record.metadata,
                    "bronze_record_id": record.record_id,
                    "cleaned_at": datetime.utcnow().isoformat(),
                },
            )
            self._layers["silver"].append(silver_record)
            records_out += 1

        job.records_out = records_out
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        self._transform_jobs[job_id] = job
        return job

    def transform_silver_to_gold(
        self,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TransformJob:
        """
        Aggregate Silver data to Gold analytics-ready format.

        Gold aggregation:
        - Group by source
        - Count records per source
        - Compute summary statistics
        """
        job_id = str(uuid.uuid4())
        job = TransformJob(
            job_id=job_id,
            source_layer="silver",
            target_layer="gold",
            status="running",
        )

        silver_records = self._layers["silver"]
        if source_filter:
            silver_records = [r for r in silver_records if r.source == source_filter]
        if limit:
            silver_records = silver_records[:limit]

        job.records_in = len(silver_records)

        # Aggregate by source
        source_groups: dict[str, list[MedallionRecord]] = {}
        for record in silver_records:
            source_groups.setdefault(record.source, []).append(record)

        records_out = 0
        for source, records in source_groups.items():
            # Collect all numeric values for stats
            numeric_values: list[float] = []
            all_fields: set[str] = set()
            for r in records:
                all_fields.update(r.data.keys())
                for v in r.data.values():
                    if isinstance(v, (int, float)):
                        numeric_values.append(float(v))

            gold_data = {
                "source": source,
                "record_count": len(records),
                "fields": sorted(all_fields),
                "numeric_summary": {
                    "count": len(numeric_values),
                    "sum": sum(numeric_values) if numeric_values else 0,
                    "avg": sum(numeric_values) / len(numeric_values) if numeric_values else 0,
                    "min": min(numeric_values) if numeric_values else 0,
                    "max": max(numeric_values) if numeric_values else 0,
                },
                "aggregated_at": datetime.utcnow().isoformat(),
            }

            gold_record = MedallionRecord(
                record_id=str(uuid.uuid4()),
                layer="gold",
                source=source,
                data=gold_data,
                metadata={
                    "silver_record_count": len(records),
                    "aggregated_at": datetime.utcnow().isoformat(),
                },
            )
            self._layers["gold"].append(gold_record)
            records_out += 1

        job.records_out = records_out
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        self._transform_jobs[job_id] = job
        return job

    def get_transform_job(self, job_id: str) -> Optional[TransformJob]:
        """Get a transform job by ID."""
        return self._transform_jobs.get(job_id)


# Singleton repository instance
repo = DataLakeRepository()
