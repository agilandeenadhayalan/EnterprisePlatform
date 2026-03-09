"""
Domain models for the data catalog service.

Represents datasets and their metadata in the catalog registry.
"""

from datetime import datetime
from typing import Any, Optional


class Dataset:
    """A registered dataset in the catalog."""

    def __init__(
        self,
        id: str,
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.store = store  # e.g., "clickhouse", "minio", "postgres"
        self.location = location  # e.g., table name or bucket/path
        self.schema_fields = schema_fields or []
        self.format = format
        self.owner = owner
        self.tags = tags or []
        self.size_bytes = size_bytes
        self.record_count = record_count
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "store": self.store,
            "location": self.location,
            "schema_fields": self.schema_fields,
            "format": self.format,
            "owner": self.owner,
            "tags": self.tags,
            "size_bytes": self.size_bytes,
            "record_count": self.record_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
