"""
Feature Store client for online and offline feature serving.

Provides a unified interface for storing and retrieving ML features
across two backing stores:

  - **Online store** (Redis):  Low-latency reads for real-time inference.
    Features are stored as individual keys with configurable TTL.
  - **Offline store** (ClickHouse):  Columnar storage for historical
    features used in training.  Supports point-in-time joins to prevent
    data leakage.

Falls back gracefully to in-memory dictionaries when Redis or ClickHouse
are unavailable, following the same pattern as the ClickHouse client
wrapper used throughout Phase 3 services.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Optional dependency: redis ──
try:
    import redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False


class FeatureStoreClient:
    """Unified online/offline feature store backed by Redis and ClickHouse.

    Parameters
    ----------
    redis_host : str
        Hostname of the Redis instance used for the online store.
    redis_port : int
        Port of the Redis instance.
    clickhouse_client : object or None
        An instance of ``ClickHouseClient`` from ``mobility_common.clickhouse``
        used for the offline store.  May be ``None`` if offline features are
        not needed.

    Notes
    -----
    When Redis is not installed or unreachable the client stores features in
    a plain Python dictionary so that service code can develop and test
    without a running Redis instance.  The same applies to ClickHouse via
    the offline mock store.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        clickhouse_client: Any = None,
    ) -> None:
        self.redis_host = redis_host
        self.redis_port = redis_port
        self._ch = clickhouse_client

        # Online store — Redis or in-memory fallback
        self._redis: Any = None
        self._online_mock: Dict[str, Dict[str, Any]] = {}
        self._online_mock_ttl: Dict[str, float] = {}
        self._use_mock_online = True

        if _HAS_REDIS:
            try:
                self._redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                )
                self._redis.ping()
                self._use_mock_online = False
                logger.info(
                    "FeatureStore online store connected to Redis %s:%s",
                    redis_host,
                    redis_port,
                )
            except Exception as exc:
                logger.warning(
                    "Redis connection failed (%s) — online store running in mock mode",
                    exc,
                )
        else:
            logger.warning(
                "redis package not installed — online store running in mock mode"
            )

        # Offline store — ClickHouse or in-memory fallback
        self._offline_mock: List[Dict[str, Any]] = []
        self._use_mock_offline = clickhouse_client is None or not getattr(
            clickhouse_client, "is_connected", False
        )
        if self._use_mock_offline:
            logger.warning(
                "ClickHouse client unavailable — offline store running in mock mode"
            )
        else:
            logger.info("FeatureStore offline store using ClickHouse")

    # ── Online store ──

    def put_online_feature(
        self,
        entity_id: str,
        feature_name: str,
        value: Any,
        ttl: int = 3600,
    ) -> None:
        """Store a single feature value in the online store.

        Parameters
        ----------
        entity_id : str
            Unique identifier for the entity (e.g. vehicle id, user id).
        feature_name : str
            Name of the feature to store.
        value : Any
            Feature value.  Will be JSON-serialised for Redis storage.
        ttl : int
            Time-to-live in seconds (default 3600 = 1 hour).
        """
        key = f"feature:{entity_id}:{feature_name}"
        serialised = json.dumps(value)

        if not self._use_mock_online:
            try:
                self._redis.set(key, serialised, ex=ttl)
                logger.debug("Redis SET %s (ttl=%s)", key, ttl)
                return
            except Exception as exc:
                logger.warning("Redis SET failed (%s) — falling back to mock", exc)

        # Mock fallback
        self._online_mock[key] = serialised
        self._online_mock_ttl[key] = time.time() + ttl
        logger.debug("Mock SET %s (ttl=%s)", key, ttl)

    def get_online_features(
        self,
        entity_id: str,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """Retrieve one or more features for an entity from the online store.

        Parameters
        ----------
        entity_id : str
            Entity identifier.
        feature_names : list[str]
            List of feature names to retrieve.

        Returns
        -------
        dict
            Mapping of feature name to value.  Missing features are ``None``.
        """
        result: Dict[str, Any] = {}

        for name in feature_names:
            key = f"feature:{entity_id}:{name}"
            raw: Optional[str] = None

            if not self._use_mock_online:
                try:
                    raw = self._redis.get(key)
                except Exception as exc:
                    logger.warning("Redis GET failed (%s) — trying mock", exc)

            if raw is None:
                # Try mock (covers both fallback and mock-only mode)
                raw = self._online_mock.get(key)
                if raw is not None:
                    # Check TTL for mock entries
                    expires = self._online_mock_ttl.get(key, 0)
                    if time.time() > expires:
                        del self._online_mock[key]
                        del self._online_mock_ttl[key]
                        raw = None

            result[name] = json.loads(raw) if raw is not None else None

        logger.debug(
            "Online features for %s: %d/%d found",
            entity_id,
            sum(1 for v in result.values() if v is not None),
            len(feature_names),
        )
        return result

    # ── Offline store ──

    def put_offline_features(
        self,
        entity_type: str,
        entity_id: str,
        features_dict: Dict[str, Any],
        timestamp: str,
    ) -> None:
        """Persist a feature vector in the offline (historical) store.

        Parameters
        ----------
        entity_type : str
            The kind of entity (e.g. ``"vehicle"``, ``"station"``).
        entity_id : str
            Unique identifier for the entity.
        features_dict : dict
            Mapping of feature name to value.
        timestamp : str
            ISO-8601 timestamp for this observation.
        """
        row = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": timestamp,
            **features_dict,
        }

        if not self._use_mock_offline:
            try:
                # Delegate to ClickHouse client (async-compat via the
                # same fire-and-forget pattern used elsewhere)
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        self._ch.insert_dicts("ml_feature_store", [row])
                    )
                else:
                    loop.run_until_complete(
                        self._ch.insert_dicts("ml_feature_store", [row])
                    )
                logger.debug(
                    "Offline feature stored for %s/%s at %s",
                    entity_type,
                    entity_id,
                    timestamp,
                )
                return
            except Exception as exc:
                logger.warning(
                    "ClickHouse insert failed (%s) — storing in mock", exc
                )

        self._offline_mock.append(row)
        logger.debug(
            "Mock offline feature stored for %s/%s at %s",
            entity_type,
            entity_id,
            timestamp,
        )

    def get_offline_features(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        point_in_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query historical features from the offline store.

        Parameters
        ----------
        entity_ids : list[str]
            Entity identifiers to query.
        feature_names : list[str]
            Feature names to return.
        point_in_time : str or None
            Optional ISO-8601 timestamp.  When provided, only features
            recorded on or before this time are returned.

        Returns
        -------
        list[dict]
            One dict per matching row with ``entity_id``, ``timestamp``,
            and the requested feature columns.
        """
        if not self._use_mock_offline:
            try:
                import asyncio

                cols = ", ".join(["entity_id", "timestamp"] + feature_names)
                ids_str = ", ".join(f"'{eid}'" for eid in entity_ids)
                query = (
                    f"SELECT {cols} FROM ml_feature_store "
                    f"WHERE entity_id IN ({ids_str})"
                )
                if point_in_time:
                    query += f" AND timestamp <= '{point_in_time}'"
                query += " ORDER BY timestamp DESC"

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Cannot await inside sync context — fall through to mock
                    raise RuntimeError("Cannot run sync in async loop")
                return loop.run_until_complete(self._ch.execute(query))
            except Exception as exc:
                logger.warning(
                    "ClickHouse offline query failed (%s) — using mock", exc
                )

        # Mock fallback
        results: List[Dict[str, Any]] = []
        for row in self._offline_mock:
            if row.get("entity_id") not in entity_ids:
                continue
            if point_in_time and row.get("timestamp", "") > point_in_time:
                continue
            filtered = {
                "entity_id": row["entity_id"],
                "timestamp": row["timestamp"],
            }
            for fn in feature_names:
                filtered[fn] = row.get(fn)
            results.append(filtered)

        logger.debug(
            "Offline query returned %d rows for %d entities",
            len(results),
            len(entity_ids),
        )
        return results

    # ── Training utilities ──

    def point_in_time_join(
        self,
        labels: List[Dict[str, Any]],
        features: List[Dict[str, Any]],
        entity_col: str = "entity_id",
        time_col: str = "timestamp",
        lookback_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Join labels with the most recent features *before* each label time.

        This prevents data leakage by ensuring that only features known at
        or before the label timestamp are used for training.

        Parameters
        ----------
        labels : list[dict]
            Each dict must contain at least ``entity_col`` and ``time_col``.
        features : list[dict]
            Feature rows, each with ``entity_col`` and ``time_col``.
        entity_col : str
            Column name used to match entities (default ``"entity_id"``).
        time_col : str
            Column name with ISO-8601 timestamps (default ``"timestamp"``).
        lookback_hours : int
            Maximum number of hours to look back for features (default 24).

        Returns
        -------
        list[dict]
            Merged rows.  Each label dict is augmented with the most-recent
            feature columns that fall within the lookback window.
        """
        # Index features by entity for O(n) scan per entity
        from collections import defaultdict

        feat_by_entity: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for f in features:
            feat_by_entity[f[entity_col]].append(f)
        # Sort each entity's features by time (ascending)
        for eid in feat_by_entity:
            feat_by_entity[eid].sort(key=lambda r: r[time_col])

        lookback_seconds = lookback_hours * 3600
        joined: List[Dict[str, Any]] = []

        for label in labels:
            eid = label[entity_col]
            label_time = label[time_col]
            entity_feats = feat_by_entity.get(eid, [])

            best: Optional[Dict[str, Any]] = None
            for f in entity_feats:
                feat_time = f[time_col]
                if feat_time > label_time:
                    break  # features are sorted — no point continuing
                # Simple ISO string comparison works for same-format timestamps
                best = f

            merged = dict(label)
            if best is not None:
                # Rough check for lookback window using string comparison
                # (sufficient for ISO-8601 with same tz)
                time_diff = self._iso_diff_seconds(best[time_col], label_time)
                if time_diff <= lookback_seconds:
                    for k, v in best.items():
                        if k not in (entity_col, time_col):
                            merged[k] = v
            joined.append(merged)

        logger.debug(
            "Point-in-time join: %d labels, %d features -> %d rows",
            len(labels),
            len(features),
            len(joined),
        )
        return joined

    # ── Helpers ──

    @staticmethod
    def _iso_diff_seconds(earlier: str, later: str) -> float:
        """Approximate seconds between two ISO-8601 timestamp strings.

        Uses stdlib ``datetime`` to parse.  Returns ``float('inf')`` if
        parsing fails so the lookback check is skipped.
        """
        from datetime import datetime

        try:
            fmt = "%Y-%m-%dT%H:%M:%S"
            # Truncate fractional seconds and tz for simple parsing
            t1 = datetime.strptime(earlier[:19], fmt)
            t2 = datetime.strptime(later[:19], fmt)
            return (t2 - t1).total_seconds()
        except (ValueError, TypeError):
            return float("inf")
