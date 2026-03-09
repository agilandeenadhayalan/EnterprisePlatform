"""
Exercise 1: Point-in-Time Feature Joins
=========================================

CONCEPT:
When training ML models, you need to join features with labels at
historical timestamps. The critical rule is: you must only use features
that were available AT THE TIME the label was generated. Using future
features = data leakage = unrealistically good training metrics that
don't hold in production.

YOUR TASK:
Implement a PointInTimeJoiner that:
1. Groups features by entity and sorts them by timestamp.
2. For each label row, finds the most recent feature values that existed
   BEFORE the label timestamp, within a lookback window.

You need to implement two methods:
- _find_latest_before(): Binary search for the latest feature before a timestamp.
- join(): The main join logic.

HINTS:
- Use Python's bisect module for efficient binary search.
- bisect.bisect_right(times, target) returns the insertion point for target,
  which means times[insertion_point - 1] is the largest value <= target.
- Remember to check the lookback window.
"""

import bisect


class PointInTimeJoiner:
    """Joins features with labels using point-in-time correctness."""

    def __init__(self, lookback_hours: int = 24) -> None:
        self.lookback_hours = lookback_hours
        self.lookback_seconds = lookback_hours * 3600

    def _find_latest_before(
        self,
        sorted_times: list[float],
        target_time: float,
    ) -> int | None:
        """Find the index of the latest timestamp that is <= target_time.

        Uses binary search for efficiency (O(log n) instead of O(n)).

        Args:
            sorted_times: List of timestamps in ascending order.
            target_time: The timestamp to search for.

        Returns:
            Index of the latest timestamp <= target_time, or None if
            no such timestamp exists.

        Examples:
            sorted_times = [100, 200, 300, 400, 500]
            _find_latest_before(sorted_times, 350) -> 2  (times[2] = 300)
            _find_latest_before(sorted_times, 500) -> 4  (times[4] = 500)
            _find_latest_before(sorted_times, 50)  -> None  (all times > 50)
        """
        # TODO: Implement (~4 lines)
        # 1. Use bisect.bisect_right to find the insertion point
        # 2. The index we want is insertion_point - 1
        # 3. Return None if the index is negative (no valid timestamp)
        raise NotImplementedError("Implement _find_latest_before using bisect")

    def join(
        self,
        labels: list[dict],
        features: list[dict],
        entity_col: str,
        time_col: str,
        feature_cols: list[str],
    ) -> list[dict]:
        """Join labels with features using point-in-time correctness.

        For each label row:
        1. Find features for the same entity.
        2. Use _find_latest_before to find the most recent feature BEFORE
           the label timestamp.
        3. Only use the feature if it's within the lookback window.

        Args:
            labels: List of dicts with entity_col, time_col, and 'label'.
            features: List of dicts with entity_col, time_col, and feature values.
            entity_col: Name of the entity identifier column.
            time_col: Name of the timestamp column.
            feature_cols: Names of the feature value columns to join.

        Returns:
            List of dicts with original label data plus matched feature values.
            Missing features are set to None. Each result includes 'feature_time'.
        """
        # TODO: Implement (~20 lines)
        # Step 1: Group features by entity (~5 lines)
        #   - Create a dict mapping entity_id -> list of (timestamp, feature_row)
        #   - Sort each entity's features by timestamp

        # Step 2: For each label, find matching features (~15 lines)
        #   - Get the entity's sorted feature list
        #   - Extract just the timestamps into a list
        #   - Use _find_latest_before to find the right index
        #   - Check if the feature is within the lookback window
        #   - Build the result dict with label data + matched features
        raise NotImplementedError("Implement the point-in-time join logic")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def _verify():
    """Run basic checks to verify your implementation."""
    joiner = PointInTimeJoiner(lookback_hours=2)

    # Test _find_latest_before
    times = [100.0, 200.0, 300.0, 400.0, 500.0]
    assert joiner._find_latest_before(times, 350.0) == 2, "Should find index 2 (time=300)"
    assert joiner._find_latest_before(times, 500.0) == 4, "Should find index 4 (time=500)"
    assert joiner._find_latest_before(times, 50.0) is None, "Should return None"
    print("[PASS] _find_latest_before works correctly")

    # Test join with point-in-time correctness
    labels = [
        {"driver_id": "d1", "timestamp": 1000.0, "label": 25.0},
        {"driver_id": "d1", "timestamp": 2000.0, "label": 30.0},
        {"driver_id": "d2", "timestamp": 1500.0, "label": 15.0},
    ]
    features = [
        {"driver_id": "d1", "timestamp": 500.0, "speed": 30.0},
        {"driver_id": "d1", "timestamp": 900.0, "speed": 35.0},
        {"driver_id": "d1", "timestamp": 1500.0, "speed": 20.0},  # AFTER label at 1000
        {"driver_id": "d2", "timestamp": 1400.0, "speed": 45.0},
    ]

    results = joiner.join(labels, features, "driver_id", "timestamp", ["speed"])

    # Label at t=1000 should get feature at t=900 (not t=1500!)
    assert results[0]["speed"] == 35.0, f"Expected 35.0, got {results[0]['speed']}"
    assert results[0]["feature_time"] == 900.0

    # Label at t=2000 should get feature at t=1500
    assert results[1]["speed"] == 20.0, f"Expected 20.0, got {results[1]['speed']}"

    # Label for d2 at t=1500 should get feature at t=1400
    assert results[2]["speed"] == 45.0, f"Expected 45.0, got {results[2]['speed']}"

    print("[PASS] Point-in-time join works correctly")
    print("[PASS] All verifications passed!")


if __name__ == "__main__":
    _verify()
