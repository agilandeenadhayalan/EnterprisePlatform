"""
Windowing Strategies for Stream Processing
=============================================

When processing an unbounded stream of events, we need a way to group
events into finite sets for aggregation. Windows define those boundaries.

THREE WINDOWING STRATEGIES:

1. **Tumbling Window** (fixed, non-overlapping)
   - Every event belongs to exactly one window.
   - Window boundaries: [0, 10), [10, 20), [20, 30), ...
   - Use case: "Count rides per minute."

2. **Sliding Window** (fixed, overlapping)
   - A window slides by a step smaller than its size.
   - Events can belong to multiple windows.
   - Use case: "Average speed over last 5 min, updated every 1 min."

3. **Session Window** (dynamic, gap-based)
   - Groups events by activity. No events for N seconds = session ends.
   - Window size varies per key.
   - Use case: "Group a driver's GPS pings into trip sessions."

LATE EVENTS:
In real systems (Flink, Spark Streaming), events can arrive out of order.
Watermarks track progress and allowed lateness handles stragglers.
This simulation uses simple wall-clock ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WindowResult:
    """The output of a closed window — immutable aggregation result."""
    start: float
    end: float
    values: tuple[float, ...]
    count: int
    total: float
    avg: float

    @staticmethod
    def from_values(start: float, end: float, values: list[float]) -> WindowResult:
        count = len(values)
        total = sum(values)
        avg = total / count if count > 0 else 0.0
        return WindowResult(
            start=start,
            end=end,
            values=tuple(values),
            count=count,
            total=round(total, 6),
            avg=round(avg, 6),
        )


class TumblingWindow:
    """
    Fixed-size, non-overlapping window.

    Events are bucketed into windows of `size_seconds` duration.
    When a new event arrives past the current window boundary,
    the old window closes and a new one opens.

    Example (size=10):
        Event at t=3  -> window [0, 10)
        Event at t=7  -> window [0, 10)
        Event at t=12 -> closes [0, 10), opens [10, 20)
    """

    def __init__(self, size_seconds: float) -> None:
        if size_seconds <= 0:
            raise ValueError("Window size must be positive")
        self.size_seconds = size_seconds
        self._active_windows: dict[float, list[float]] = {}
        self._closed: list[WindowResult] = []

    def _window_start(self, timestamp: float) -> float:
        """Compute which window a timestamp belongs to."""
        return (timestamp // self.size_seconds) * self.size_seconds

    def add(self, timestamp: float, value: float) -> None:
        """
        Add an event to the appropriate window.

        If the event's window start is different from existing active
        windows, those older windows are closed.
        """
        w_start = self._window_start(timestamp)

        # Close any windows that are older than the current event's window
        to_close = [
            start for start in self._active_windows
            if start + self.size_seconds <= timestamp
        ]
        for start in sorted(to_close):
            values = self._active_windows.pop(start)
            self._closed.append(
                WindowResult.from_values(start, start + self.size_seconds, values)
            )

        # Add to the appropriate window
        if w_start not in self._active_windows:
            self._active_windows[w_start] = []
        self._active_windows[w_start].append(value)

    def get_closed_windows(self) -> list[WindowResult]:
        """Return all closed (finalized) windows."""
        return list(self._closed)

    def flush(self) -> list[WindowResult]:
        """
        Force-close all active windows and return results.

        Used at end-of-stream to get final results from windows
        that haven't been closed by subsequent events.
        """
        for start in sorted(self._active_windows):
            values = self._active_windows[start]
            self._closed.append(
                WindowResult.from_values(start, start + self.size_seconds, values)
            )
        self._active_windows.clear()
        return list(self._closed)


class SlidingWindow:
    """
    Fixed-size, overlapping window with a slide interval.

    Each event can belong to multiple windows. A window of size S
    with slide interval D produces windows:
        [0, S), [D, S+D), [2D, S+2D), ...

    Example (size=10, slide=5):
        Event at t=3 -> belongs to [0, 10) and possibly [-5, 5) if it existed
        Event at t=7 -> belongs to [0, 10) and [5, 15)

    Sliding windows are useful when you want overlapping aggregates:
    "Average of the last 10 seconds, updated every 5 seconds."
    """

    def __init__(self, size_seconds: float, slide_seconds: float) -> None:
        if size_seconds <= 0 or slide_seconds <= 0:
            raise ValueError("Window size and slide must be positive")
        if slide_seconds > size_seconds:
            raise ValueError("Slide interval cannot exceed window size")
        self.size_seconds = size_seconds
        self.slide_seconds = slide_seconds
        self._events: list[tuple[float, float]] = []
        self._closed: list[WindowResult] = []
        self._max_timestamp: float = 0.0

    def add(self, timestamp: float, value: float) -> None:
        """Add an event. May close windows whose end <= timestamp."""
        self._events.append((timestamp, value))
        if timestamp > self._max_timestamp:
            self._max_timestamp = timestamp
        self._close_expired_windows()

    def _window_starts_for(self, timestamp: float) -> list[float]:
        """Find all window starts that contain the given timestamp."""
        starts = []
        # The earliest window start that could contain this timestamp
        earliest = timestamp - self.size_seconds + self.slide_seconds
        # Align to slide boundary
        w = max(0.0, (earliest // self.slide_seconds) * self.slide_seconds)
        while w <= timestamp:
            if w <= timestamp < w + self.size_seconds:
                starts.append(w)
            w += self.slide_seconds
        return starts

    def _close_expired_windows(self) -> None:
        """Close windows whose end time is <= max observed timestamp."""
        # Find all unique window starts from all events
        all_starts: set[float] = set()
        for ts, _ in self._events:
            for start in self._window_starts_for(ts):
                all_starts.add(start)

        closed_starts = set(r.start for r in self._closed)

        for start in sorted(all_starts):
            end = start + self.size_seconds
            if end <= self._max_timestamp and start not in closed_starts:
                values = [
                    v for ts, v in self._events
                    if start <= ts < end
                ]
                if values:
                    self._closed.append(WindowResult.from_values(start, end, values))

    def get_closed_windows(self) -> list[WindowResult]:
        """Return all closed (finalized) windows."""
        return list(self._closed)

    def flush(self) -> list[WindowResult]:
        """Force-close all remaining windows."""
        all_starts: set[float] = set()
        for ts, _ in self._events:
            for start in self._window_starts_for(ts):
                all_starts.add(start)

        closed_starts = set(r.start for r in self._closed)

        for start in sorted(all_starts):
            end = start + self.size_seconds
            if start not in closed_starts:
                values = [v for ts, v in self._events if start <= ts < end]
                if values:
                    self._closed.append(WindowResult.from_values(start, end, values))

        return list(self._closed)


class SessionWindow:
    """
    Activity-based window that extends with each event.

    A session window groups events that occur within a `gap_seconds`
    of each other. If no event arrives for longer than the gap,
    the session closes and a new one starts.

    Example (gap=5):
        Events at t=1, 3, 4 -> session [1, 4] (gap < 5 between each)
        No event until t=12 -> session [1, 4] closes
        Events at t=12, 14  -> new session [12, 14]

    Use case: Group a user's click events into browsing sessions,
    or group GPS pings into trip sessions.
    """

    def __init__(self, gap_seconds: float) -> None:
        if gap_seconds <= 0:
            raise ValueError("Gap must be positive")
        self.gap_seconds = gap_seconds
        self._current_start: float | None = None
        self._current_end: float | None = None
        self._current_values: list[float] = []
        self._closed: list[WindowResult] = []

    def add(self, timestamp: float, value: float) -> None:
        """
        Add an event. If the gap since the last event exceeds
        gap_seconds, close the current session and start a new one.
        """
        if self._current_start is None:
            # First event — start a new session
            self._current_start = timestamp
            self._current_end = timestamp
            self._current_values = [value]
        elif timestamp - self._current_end > self.gap_seconds:
            # Gap exceeded — close current session, start new one
            self._close_current()
            self._current_start = timestamp
            self._current_end = timestamp
            self._current_values = [value]
        else:
            # Within gap — extend session
            self._current_end = timestamp
            self._current_values.append(value)

    def _close_current(self) -> None:
        """Close the current session and store the result."""
        if self._current_start is not None and self._current_values:
            self._closed.append(
                WindowResult.from_values(
                    self._current_start,
                    self._current_end,  # type: ignore
                    self._current_values,
                )
            )

    def get_closed_windows(self) -> list[WindowResult]:
        """Return all closed sessions (does not include the active session)."""
        return list(self._closed)

    def flush(self) -> list[WindowResult]:
        """Force-close the active session and return all results."""
        self._close_current()
        self._current_start = None
        self._current_end = None
        self._current_values = []
        return list(self._closed)
