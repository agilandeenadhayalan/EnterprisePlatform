"""
Data Catalog repository — in-memory dataset registry.

Stores dataset metadata for the catalog. In production, this would
use PostgreSQL or a dedicated metadata store.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import Dataset


class CatalogRepository:
    """In-memory dataset catalog storage."""

    def __init__(self):
        self._datasets: dict[str, Dataset] = {}

    def create_dataset(
        self,
        name: str,
        description: str,
        store: str,
        location: str,
        schema_fields: Optional[list[dict[str, str]]] = None,
        format: str = "parquet",
        owner: Optional[str] = None,
        tags: Optional[list[str]] = None,
        size_bytes: int = 0,
        record_count: int = 0,
    ) -> Dataset:
        """Register a new dataset in the catalog."""
        dataset_id = str(uuid.uuid4())
        dataset = Dataset(
            id=dataset_id,
            name=name,
            description=description,
            store=store,
            location=location,
            schema_fields=schema_fields,
            format=format,
            owner=owner,
            tags=tags,
            size_bytes=size_bytes,
            record_count=record_count,
        )
        self._datasets[dataset_id] = dataset
        return dataset

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID."""
        return self._datasets.get(dataset_id)

    def list_datasets(
        self,
        store: Optional[str] = None,
        q: Optional[str] = None,
    ) -> list[Dataset]:
        """List datasets with optional filtering."""
        datasets = list(self._datasets.values())

        if store:
            datasets = [d for d in datasets if d.store == store]

        if q:
            q_lower = q.lower()
            datasets = [
                d for d in datasets
                if q_lower in d.name.lower()
                or q_lower in d.description.lower()
                or any(q_lower in tag.lower() for tag in d.tags)
            ]

        return datasets

    def update_dataset(self, dataset_id: str, **fields) -> Optional[Dataset]:
        """Update specific fields on a dataset."""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None

        for key, value in fields.items():
            if value is not None and hasattr(dataset, key):
                setattr(dataset, key, value)

        dataset.updated_at = datetime.utcnow()
        return dataset

    def delete_dataset(self, dataset_id: str) -> bool:
        """Remove a dataset from the catalog."""
        if dataset_id in self._datasets:
            del self._datasets[dataset_id]
            return True
        return False

    def search_datasets(self, keyword: str) -> list[Dataset]:
        """Search datasets by keyword across name, description, and tags."""
        return self.list_datasets(q=keyword)

    def get_stats(self) -> dict:
        """Get catalog statistics."""
        datasets = list(self._datasets.values())
        by_store: dict[str, int] = {}
        for d in datasets:
            by_store[d.store] = by_store.get(d.store, 0) + 1

        return {
            "total_datasets": len(datasets),
            "by_store": by_store,
            "total_size_bytes": sum(d.size_bytes for d in datasets),
            "total_records": sum(d.record_count for d in datasets),
        }


# Singleton repository instance
repo = CatalogRepository()
