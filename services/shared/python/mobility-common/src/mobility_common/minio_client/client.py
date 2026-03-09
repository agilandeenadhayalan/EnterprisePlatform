"""
MinIO client wrapper for data lake operations.

Supports JSON and Parquet read/write to the Medallion architecture
buckets (Bronze / Silver / Gold).
"""

from __future__ import annotations

import io
import json
import gzip
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

try:
    from minio import Minio
    from minio.error import S3Error
    _HAS_MINIO = True
except ImportError:
    _HAS_MINIO = False

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _HAS_ARROW = True
except ImportError:
    _HAS_ARROW = False


# ── Bucket Constants ──
BUCKET_BRONZE = "mobility-bronze"
BUCKET_SILVER = "mobility-silver"
BUCKET_GOLD = "mobility-gold"
BUCKET_CHECKPOINTS = "mobility-checkpoints"


class MinIOClient:
    """Wrapper around the minio Python client with data-lake helpers."""

    def __init__(
        self,
        endpoint: str = "localhost:9002",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        secure: bool = False,
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client: Minio | None = None
        self._connected = False

    # ── Lifecycle ──

    async def connect(self) -> None:
        if not _HAS_MINIO:
            logger.warning("minio package not installed — running in mock mode")
            return
        try:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            # Verify connectivity by listing buckets
            self._client.list_buckets()
            self._connected = True
            logger.info("Connected to MinIO at %s", self.endpoint)
        except Exception as exc:
            logger.warning("MinIO connection failed (%s) — running in mock mode", exc)
            self._connected = False

    async def close(self) -> None:
        self._client = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    # ── Bucket Operations ──

    async def ensure_bucket(self, bucket_name: str) -> None:
        """Create bucket if it doesn't exist."""
        if not self.is_connected:
            return
        if not self._client.bucket_exists(bucket_name):
            self._client.make_bucket(bucket_name)
            logger.info("Created bucket: %s", bucket_name)

    # ── JSON Operations ──

    async def put_json(
        self,
        bucket: str,
        key: str,
        data: Any,
        compress: bool = False,
    ) -> None:
        """Upload JSON data to MinIO."""
        if not self.is_connected:
            logger.debug("MinIO not connected — skipping put_json")
            return
        raw = json.dumps(data, default=str).encode("utf-8")
        content_type = "application/json"
        if compress:
            raw = gzip.compress(raw)
            content_type = "application/gzip"
            key = key if key.endswith(".gz") else key + ".gz"
        buf = io.BytesIO(raw)
        self._client.put_object(bucket, key, buf, len(raw), content_type=content_type)

    async def get_json(self, bucket: str, key: str) -> Any:
        """Download and parse JSON from MinIO."""
        if not self.is_connected:
            return None
        try:
            response = self._client.get_object(bucket, key)
            raw = response.read()
            response.close()
            response.release_conn()
            if key.endswith(".gz"):
                raw = gzip.decompress(raw)
            return json.loads(raw)
        except Exception as exc:
            logger.error("Failed to get %s/%s: %s", bucket, key, exc)
            return None

    # ── Parquet Operations ──

    async def put_parquet(
        self,
        bucket: str,
        key: str,
        table: pa.Table | None = None,
        records: list[dict] | None = None,
    ) -> None:
        """Write Parquet data to MinIO from a PyArrow Table or list of dicts."""
        if not self.is_connected:
            logger.debug("MinIO not connected — skipping put_parquet")
            return
        if not _HAS_ARROW:
            logger.warning("pyarrow not installed — cannot write Parquet")
            return

        if table is None and records is not None:
            table = pa.Table.from_pylist(records)
        if table is None:
            return

        buf = io.BytesIO()
        pq.write_table(table, buf)
        buf.seek(0)
        data = buf.getvalue()
        self._client.put_object(
            bucket, key, io.BytesIO(data), len(data),
            content_type="application/octet-stream",
        )

    async def get_parquet(self, bucket: str, key: str) -> pa.Table | None:
        """Read a Parquet file from MinIO and return as PyArrow Table."""
        if not self.is_connected or not _HAS_ARROW:
            return None
        try:
            response = self._client.get_object(bucket, key)
            raw = response.read()
            response.close()
            response.release_conn()
            return pq.read_table(io.BytesIO(raw))
        except Exception as exc:
            logger.error("Failed to read Parquet %s/%s: %s", bucket, key, exc)
            return None

    # ── Listing ──

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = True,
    ) -> list[str]:
        """List object keys under a prefix."""
        if not self.is_connected:
            return []
        return [
            obj.object_name
            for obj in self._client.list_objects(bucket, prefix=prefix, recursive=recursive)
        ]

    # ── Helpers ──

    @staticmethod
    def make_key(domain: str, topic: str, partition: int = 0, offset: int = 0) -> str:
        """Generate a Bronze-layer key with date partitioning."""
        now = datetime.utcnow()
        return (
            f"kafka/{topic}/year={now.year}/month={now.month:02d}/"
            f"day={now.day:02d}/{topic}-p{partition}-{offset}.json.gz"
        )

    # ── Health ──

    async def health_check(self) -> bool:
        if not self.is_connected:
            return False
        try:
            self._client.list_buckets()
            return True
        except Exception:
            return False
