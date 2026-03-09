"""
Kafka Consumer Locations repository — in-memory archive simulation for MinIO Bronze layer.
"""

import json
import time
from datetime import datetime, timezone
from typing import Optional

from models import ArchiveStats, ArchivedFile


class LocationArchiveRepository:
    """In-memory archive storage simulating MinIO Bronze layer writes for location events."""

    def __init__(self, bucket: str = "bronze", prefix: str = "kafka/location.events.v1"):
        self.bucket = bucket
        self.prefix = prefix
        self.archived_files: list[ArchivedFile] = []
        self.stats = ArchiveStats()
        self._start_time = time.time()

    def _generate_file_path(self, topic: str, timestamp: datetime) -> str:
        """Generate MinIO path: kafka/location.events.v1/year=YYYY/month=MM/day=DD/batch_HHMMSS.json.gz"""
        return (
            f"{self.prefix}/"
            f"year={timestamp.year}/"
            f"month={timestamp.month:02d}/"
            f"day={timestamp.day:02d}/"
            f"batch_{timestamp.strftime('%H%M%S')}_{int(time.time() * 1000) % 10000}.json.gz"
        )

    def archive_batch(self, events: list[dict], topic: str = "location.events.v1") -> tuple[str, int]:
        """
        Archive a batch of location events as a compressed JSON file.
        Returns (file_path, file_size).
        """
        if not events:
            return "", 0

        now = datetime.now(timezone.utc)
        file_path = self._generate_file_path(topic, now)

        # Simulate JSON serialization and compression
        json_data = json.dumps(events, default=str)
        file_size = len(json_data.encode("utf-8"))

        archived_file = ArchivedFile(
            file_path=f"{self.bucket}/{file_path}",
            file_size=file_size,
            event_count=len(events),
            created_at=now.isoformat(),
            topic=topic,
        )
        self.archived_files.append(archived_file)

        # Update stats
        self.stats.events_archived += len(events)
        self.stats.files_written += 1
        self.stats.bytes_written += file_size
        self.stats.last_archived_at = now.isoformat()

        return archived_file.file_path, file_size

    def get_stats(self) -> ArchiveStats:
        """Return current archive statistics."""
        self.stats.uptime_seconds = round(time.time() - self._start_time, 2)
        return self.stats

    def list_files(self) -> list[ArchivedFile]:
        """List all archived files."""
        return self.archived_files

    def reset(self):
        """Reset all state."""
        self.archived_files.clear()
        self.stats = ArchiveStats()
        self._start_time = time.time()
