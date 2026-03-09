"""
Stream Processor Metrics repository — tumbling window aggregation in-memory.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from models import MetricEvent, WindowedAggregate, WindowState


class _Window:
    """Internal representation of a tumbling window."""

    def __init__(self, key: str, metric_name: str, start: datetime, end: datetime, dimensions: dict):
        self.key = key
        self.metric_name = metric_name
        self.start = start
        self.end = end
        self.dimensions = dimensions
        self.values: list[float] = []
        self.is_open = True

    def add(self, value: float):
        self.values.append(value)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def sum_value(self) -> float:
        return sum(self.values) if self.values else 0.0

    @property
    def avg_value(self) -> float:
        return self.sum_value / self.count if self.count > 0 else 0.0

    @property
    def min_value(self) -> float:
        return min(self.values) if self.values else 0.0

    @property
    def max_value(self) -> float:
        return max(self.values) if self.values else 0.0


class MetricsProcessorRepository:
    """Tumbling window aggregation for metric events."""

    def __init__(self, window_size_seconds: int = 60):
        self.window_size_seconds = window_size_seconds
        self.active_windows: dict[str, _Window] = {}
        self.flushed_aggregates: list[WindowedAggregate] = []

        # Stats
        self.events_processed = 0
        self.events_failed = 0
        self.windows_created = 0
        self.windows_flushed = 0
        self.last_processed_at: Optional[str] = None
        self._start_time = time.time()

    def _get_window_key(self, metric_name: str, timestamp: datetime) -> tuple[str, datetime, datetime]:
        """Calculate the window key and boundaries for a given timestamp."""
        epoch = datetime(2020, 1, 1, tzinfo=timestamp.tzinfo if timestamp.tzinfo else None)
        total_seconds = (timestamp - epoch).total_seconds()
        window_number = int(total_seconds // self.window_size_seconds)
        window_start = epoch + timedelta(seconds=window_number * self.window_size_seconds)
        window_end = window_start + timedelta(seconds=self.window_size_seconds)
        key = f"{metric_name}:{window_number}"
        return key, window_start, window_end

    def process_batch(self, events: list[dict]) -> tuple[int, int, int]:
        """
        Process a batch of metric events into tumbling windows.
        Returns (accepted, failed, windows_updated).
        """
        accepted = 0
        failed = 0
        windows_touched: set[str] = set()

        for raw in events:
            try:
                event = MetricEvent(**raw)
                ts = datetime.fromisoformat(event.timestamp)
                key, w_start, w_end = self._get_window_key(event.metric_name, ts)

                if key not in self.active_windows:
                    self.active_windows[key] = _Window(
                        key=key,
                        metric_name=event.metric_name,
                        start=w_start,
                        end=w_end,
                        dimensions=event.dimensions,
                    )
                    self.windows_created += 1

                self.active_windows[key].add(event.metric_value)
                windows_touched.add(key)
                accepted += 1
                self.events_processed += 1
            except Exception:
                failed += 1
                self.events_failed += 1

        self.last_processed_at = datetime.now(timezone.utc).isoformat()
        return accepted, failed, len(windows_touched)

    def get_active_windows(self) -> list[WindowState]:
        """Return state of all active (open) windows."""
        return [
            WindowState(
                window_key=w.key,
                metric_name=w.metric_name,
                window_start=w.start.isoformat(),
                window_end=w.end.isoformat(),
                event_count=w.count,
                current_sum=round(w.sum_value, 4),
                current_min=round(w.min_value, 4),
                current_max=round(w.max_value, 4),
                is_open=w.is_open,
            )
            for w in self.active_windows.values()
            if w.is_open
        ]

    def flush_all_windows(self) -> list[WindowedAggregate]:
        """Close and flush all active windows. Returns the aggregated results."""
        results: list[WindowedAggregate] = []
        now = datetime.now(timezone.utc)

        for w in list(self.active_windows.values()):
            if w.is_open and w.count > 0:
                agg = WindowedAggregate(
                    window_key=w.key,
                    metric_name=w.metric_name,
                    window_start=w.start,
                    window_end=w.end,
                    count=w.count,
                    sum_value=round(w.sum_value, 4),
                    avg_value=round(w.avg_value, 4),
                    min_value=round(w.min_value, 4),
                    max_value=round(w.max_value, 4),
                    dimensions=w.dimensions,
                    flushed_at=now,
                )
                results.append(agg)
                self.flushed_aggregates.append(agg)
                w.is_open = False
                self.windows_flushed += 1

        # Remove closed windows
        self.active_windows = {
            k: v for k, v in self.active_windows.items() if v.is_open
        }

        return results

    def get_stats(self) -> dict:
        """Return processing statistics."""
        return {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "windows_created": self.windows_created,
            "windows_flushed": self.windows_flushed,
            "active_window_count": len(self.active_windows),
            "last_processed_at": self.last_processed_at,
            "uptime_seconds": round(time.time() - self._start_time, 2),
        }

    def reset(self):
        """Reset all state."""
        self.active_windows.clear()
        self.flushed_aggregates.clear()
        self.events_processed = 0
        self.events_failed = 0
        self.windows_created = 0
        self.windows_flushed = 0
        self.last_processed_at = None
        self._start_time = time.time()
