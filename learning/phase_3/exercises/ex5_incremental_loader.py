"""
Exercise 5: Incremental Data Loader
======================================

The ETL module demonstrated watermark-based incremental loading.
Now implement your own version.

TASK:
Build an incremental loader that:
1. Tracks a high watermark per source.
2. Extracts only new records since the watermark.
3. Updates the watermark after successful loading.
4. Does NOT advance the watermark on failure.

WHY incremental:
- Full loads are slow and wasteful for large datasets.
- Incremental loads only process new data (fast, efficient).
- The watermark ensures no data is missed between runs.
"""


class IncrementalDataLoader:
    """
    TODO: Implement an incremental data loader.

    The loader should:
    1. Track a high watermark per source (e.g., max updated_at)
    2. Extract only new records since the watermark
    3. Update watermark after successful load
    4. Handle failures (don't advance watermark if load fails)
    """

    def __init__(self, watermark_column: str = "updated_at") -> None:
        """
        Initialize the loader.

        Args:
            watermark_column: The column to use as the watermark.

        Hints:
        - Store watermarks in a dict keyed by source name.
        - Track load statistics for reporting.
        """
        self.watermark_column = watermark_column
        # TODO: Initialize (~2 lines)
        raise NotImplementedError("Initialize loader")

    def get_watermark(self, source: str) -> str | None:
        """Get the current watermark for a source. None if first run."""
        # TODO: Implement (~1 line)
        raise NotImplementedError("Get watermark")

    def extract(self, source: str, all_records: list[dict]) -> list[dict]:
        """
        Extract records newer than the watermark.

        If no watermark exists (first run), return ALL records.
        Otherwise, return only records where watermark_column > watermark.
        """
        # TODO: Implement (~6 lines)
        raise NotImplementedError("Extract new records")

    def load(
        self,
        source: str,
        all_records: list[dict],
        destination: list[dict],
        simulate_failure: bool = False,
    ) -> dict:
        """
        Extract new records and load them to the destination.

        Steps:
        1. Extract new records using extract().
        2. If simulate_failure is True, DON'T load or advance watermark.
        3. Otherwise, append to destination and advance watermark.

        Returns a dict with:
        - source, records_extracted, records_loaded
        - old_watermark, new_watermark
        - is_full_load (True if first run)
        """
        # TODO: Implement (~15 lines)
        raise NotImplementedError("Load data")


# ── Verification ──


def test_first_run_full_load():
    loader = IncrementalDataLoader(watermark_column="ts")
    dest: list[dict] = []
    source = [
        {"id": 1, "ts": "2024-01-01"},
        {"id": 2, "ts": "2024-01-02"},
    ]
    result = loader.load("src", source, dest)
    assert result["is_full_load"] is True
    assert result["records_loaded"] == 2
    assert len(dest) == 2


def test_incremental_load():
    loader = IncrementalDataLoader(watermark_column="ts")
    dest: list[dict] = []
    source = [
        {"id": 1, "ts": "2024-01-01"},
        {"id": 2, "ts": "2024-01-02"},
    ]
    loader.load("src", source, dest)
    source.append({"id": 3, "ts": "2024-01-03"})
    result = loader.load("src", source, dest)
    assert result["is_full_load"] is False
    assert result["records_loaded"] == 1
    assert len(dest) == 3


def test_failure_no_watermark_advance():
    loader = IncrementalDataLoader(watermark_column="ts")
    dest: list[dict] = []
    source = [{"id": 1, "ts": "2024-01-01"}]
    loader.load("src", source, dest)
    old_wm = loader.get_watermark("src")
    source.append({"id": 2, "ts": "2024-01-02"})
    result = loader.load("src", source, dest, simulate_failure=True)
    assert result["records_loaded"] == 0
    assert loader.get_watermark("src") == old_wm


def test_no_new_records():
    loader = IncrementalDataLoader(watermark_column="ts")
    dest: list[dict] = []
    source = [{"id": 1, "ts": "2024-01-01"}]
    loader.load("src", source, dest)
    result = loader.load("src", source, dest)
    assert result["records_loaded"] == 0


if __name__ == "__main__":
    try:
        test_first_run_full_load()
        test_incremental_load()
        test_failure_no_watermark_advance()
        test_no_new_records()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
