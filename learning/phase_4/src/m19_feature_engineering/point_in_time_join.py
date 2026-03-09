"""
Point-in-Time Joins for Feature Engineering
=============================================

This is the single most critical concept in ML feature engineering.

THE PROBLEM:
When training a model, you need to join labels (what you're predicting) with
features (the inputs). A naive approach takes the LATEST feature values, but
this causes **data leakage** -- you're using information from the future that
wouldn't have been available when the prediction was actually needed.

EXAMPLE:
Suppose you're training a model to predict trip duration. A label row says:
    "Trip started at 2024-01-15 14:00, duration was 25 minutes"

A feature might be "average_zone_speed". If the zone speed was updated at:
    - 13:00: 30 mph
    - 14:30: 15 mph (rush hour started)

The CORRECT feature value is 30 mph (the value known at 14:00).
A naive join might use 15 mph (the latest value), which is LEAKAGE because
that speed wasn't known when the trip started.

THE CONSEQUENCE:
Data leakage makes your model look great during training (unrealistically good
metrics) but perform poorly in production -- because in production, you only
have access to features that exist RIGHT NOW, not from the future.

THE SOLUTION:
Point-in-time joins ensure that for each label row, we only use feature values
that were available BEFORE the label's timestamp, within a reasonable lookback
window.
"""

from __future__ import annotations

import bisect


class PointInTimeJoiner:
    """Joins features with labels using temporal correctness.

    For each label row, finds the most recent feature values that existed
    BEFORE the label timestamp, within a configurable lookback window.

    This prevents data leakage by ensuring no future information is used
    during training.
    """

    def __init__(self, lookback_hours: int = 24) -> None:
        """Initialize the joiner.

        Args:
            lookback_hours: Maximum hours to look back for feature values.
                           If no feature exists within this window, the
                           feature value will be None (missing).
        """
        if lookback_hours <= 0:
            raise ValueError("lookback_hours must be positive")
        self.lookback_hours = lookback_hours
        self.lookback_seconds = lookback_hours * 3600

    def join(
        self,
        labels: list[dict],
        features: list[dict],
        entity_col: str,
        time_col: str,
        feature_cols: list[str],
    ) -> list[dict]:
        """Join labels with features using point-in-time correctness.

        For each label row, finds the most recent feature row for the same
        entity where feature_time <= label_time, within the lookback window.

        Args:
            labels: List of dicts, each containing entity_col, time_col,
                    and a 'label' key with the target value.
            features: List of dicts, each containing entity_col, time_col,
                      and one or more feature value columns.
            entity_col: Name of the entity identifier column.
            time_col: Name of the timestamp column (unix timestamp float).
            feature_cols: Names of the feature value columns to join.

        Returns:
            List of dicts with original label data plus matched feature
            values. Missing features are set to None. Each result also
            includes 'feature_time' showing when the matched features
            were computed.
        """
        # Step 1: Group features by entity and sort by time
        entity_features: dict[str, list[tuple[float, dict]]] = {}
        for feat_row in features:
            entity_id = feat_row[entity_col]
            timestamp = feat_row[time_col]
            if entity_id not in entity_features:
                entity_features[entity_id] = []
            entity_features[entity_id].append((timestamp, feat_row))

        # Sort each entity's features by timestamp
        for entity_id in entity_features:
            entity_features[entity_id].sort(key=lambda x: x[0])

        # Step 2: For each label, find the latest feature BEFORE label time
        results = []
        for label_row in labels:
            entity_id = label_row[entity_col]
            label_time = label_row[time_col]

            # Start with label data
            result = dict(label_row)

            # Default: no features found
            for col in feature_cols:
                result[col] = None
            result["feature_time"] = None

            # Look up features for this entity
            if entity_id in entity_features:
                entity_feat_list = entity_features[entity_id]
                times = [t for t, _ in entity_feat_list]

                # Binary search: find rightmost feature time <= label_time
                idx = bisect.bisect_right(times, label_time) - 1

                if idx >= 0:
                    feat_time, feat_row = entity_feat_list[idx]
                    age = label_time - feat_time

                    # Only use if within lookback window
                    if age <= self.lookback_seconds:
                        for col in feature_cols:
                            result[col] = feat_row.get(col)
                        result["feature_time"] = feat_time

            results.append(result)

        return results

    def validate_no_leakage(
        self,
        joined_data: list[dict],
        label_time_col: str,
        feature_time_col: str,
    ) -> list[dict]:
        """Verify that no feature timestamp comes after the label timestamp.

        This is a safety check you should always run after joining.

        Args:
            joined_data: Output from the join() method.
            label_time_col: Column name for label timestamps.
            feature_time_col: Column name for feature timestamps.

        Returns:
            List of violation dicts with 'index', 'label_time', 'feature_time',
            and 'leak_seconds' for any rows where leakage was detected.
            Empty list means no leakage.
        """
        violations = []
        for i, row in enumerate(joined_data):
            feat_time = row.get(feature_time_col)
            label_time = row.get(label_time_col)

            if feat_time is not None and label_time is not None:
                if feat_time > label_time:
                    violations.append({
                        "index": i,
                        "label_time": label_time,
                        "feature_time": feat_time,
                        "leak_seconds": feat_time - label_time,
                    })
        return violations


class NaiveJoiner:
    """WRONG approach -- uses latest features regardless of timestamp.

    This class demonstrates what NOT to do. It joins by entity only,
    always using the most recent feature values. This causes data leakage
    because the latest features may contain information from AFTER the
    label was generated.

    Included for educational comparison with PointInTimeJoiner.
    """

    def join(
        self,
        labels: list[dict],
        features: list[dict],
        entity_col: str,
        feature_cols: list[str],
    ) -> list[dict]:
        """Join labels with the LATEST features per entity (WRONG!).

        This is the incorrect approach that causes data leakage.
        Always use PointInTimeJoiner instead.

        Args:
            labels: List of label dicts.
            features: List of feature dicts.
            entity_col: Entity identifier column name.
            feature_cols: Feature value column names.

        Returns:
            Joined data using latest features regardless of timing.
        """
        # Find latest feature row per entity (ignoring time -- this is the bug!)
        latest_features: dict[str, dict] = {}
        for feat_row in features:
            entity_id = feat_row[entity_col]
            # Just overwrite -- last row wins (often the most recent)
            latest_features[entity_id] = feat_row

        results = []
        for label_row in labels:
            entity_id = label_row[entity_col]
            result = dict(label_row)

            if entity_id in latest_features:
                feat_row = latest_features[entity_id]
                for col in feature_cols:
                    result[col] = feat_row.get(col)
            else:
                for col in feature_cols:
                    result[col] = None

            results.append(result)

        return results
