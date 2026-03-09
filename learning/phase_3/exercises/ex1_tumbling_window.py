"""
Exercise 1: Tumbling Window Aggregator
=========================================

The windowing module demonstrated TumblingWindow for stream processing.
Now implement your own version from scratch.

A tumbling window groups events into fixed-size, non-overlapping time windows.
When a new event arrives past the current window boundary, the old window
closes and becomes available for reading.

Example (window_size=10):
    Event t=3  -> window [0, 10)
    Event t=7  -> window [0, 10)
    Event t=12 -> closes [0, 10), opens [10, 20)

WHY tumbling windows:
- Simple to implement and reason about.
- Each event belongs to exactly one window.
- Perfect for "count per minute" or "sum per hour" aggregations.
"""


class TumblingWindowAggregator:
    """
    TODO: Implement a tumbling window that:
    1. Groups events into fixed-size time windows
    2. Computes count, sum, avg per window
    3. Closes windows when new events arrive past window boundary
    """

    def __init__(self, window_size: float) -> None:
        """
        Initialize with window size in seconds.

        Hints:
        - Track the current active window's start time.
        - Keep a buffer of values for the active window.
        - Keep a list of closed window results.
        """
        self.window_size = window_size
        # TODO: Initialize your data structures (~3 lines)
        raise NotImplementedError("Initialize window data structures")

    def _window_start_for(self, timestamp: float) -> float:
        """
        Compute which window a timestamp belongs to.

        Hint: Use integer division to find the window boundary.
        Example: timestamp=7, window_size=10 -> window_start=0
                 timestamp=12, window_size=10 -> window_start=10
        """
        # TODO: Implement (~1 line)
        raise NotImplementedError("Compute window start")

    def add(self, timestamp: float, value: float) -> None:
        """
        Add an event to the appropriate window.

        Steps:
        1. Find which window this timestamp belongs to.
        2. If it's a different window than the active one, close the active window.
        3. Add the value to the (new) active window's buffer.

        Hint: Check if the new window start differs from the current one.
        """
        # TODO: Implement (~10 lines)
        raise NotImplementedError("Add event to window")

    def _close_window(self, start: float, values: list[float]) -> dict:
        """
        Close a window and compute its aggregations.

        Returns a dict with: start, end, count, sum, avg.

        Hint: avg = sum / count (handle empty windows).
        """
        # TODO: Implement (~8 lines)
        raise NotImplementedError("Close window with aggregations")

    def get_closed_windows(self) -> list[dict]:
        """Return all closed (finalized) windows."""
        # TODO: Implement (~1 line)
        raise NotImplementedError("Return closed windows")

    def flush(self) -> list[dict]:
        """
        Force-close the active window and return all results.

        Used at end-of-stream to finalize the last window.
        """
        # TODO: Implement (~4 lines)
        raise NotImplementedError("Flush active window")


# ── Verification ──


def test_basic_tumbling():
    tw = TumblingWindowAggregator(window_size=10)
    tw.add(3, 5.0)
    tw.add(7, 3.0)
    tw.add(12, 4.0)
    closed = tw.get_closed_windows()
    assert len(closed) == 1, f"Expected 1 closed window, got {len(closed)}"
    assert closed[0]["count"] == 2, f"Expected count=2, got {closed[0]['count']}"
    assert closed[0]["sum"] == 8.0, f"Expected sum=8.0, got {closed[0]['sum']}"
    assert closed[0]["avg"] == 4.0, f"Expected avg=4.0, got {closed[0]['avg']}"


def test_flush():
    tw = TumblingWindowAggregator(window_size=10)
    tw.add(3, 10.0)
    tw.add(5, 20.0)
    results = tw.flush()
    assert len(results) == 1
    assert results[0]["count"] == 2


def test_multiple_windows():
    tw = TumblingWindowAggregator(window_size=5)
    tw.add(1, 10)
    tw.add(3, 20)
    tw.add(6, 30)
    tw.add(11, 40)
    results = tw.flush()
    assert len(results) == 3


if __name__ == "__main__":
    try:
        test_basic_tumbling()
        test_flush()
        test_multiple_windows()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
