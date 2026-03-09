"""
Star Schema Modeling
======================

The star schema is the most common data warehouse modeling pattern.
It organizes data into:

- **Fact tables** — Contain measurable events (rides, transactions, clicks).
  Each row is a single event with numeric measures (fare, distance, duration)
  and foreign keys to dimension tables.

- **Dimension tables** — Contain descriptive attributes (zone name, driver name,
  date parts). Used for filtering, grouping, and labeling.

WHY star schema:
- Simple to understand (business users can navigate it).
- Excellent query performance (few joins, predictable patterns).
- Works well with BI tools (Tableau, Looker, Superset).
- Columnar databases (ClickHouse) excel at star schema queries.

RIDE ANALYTICS SCHEMA:
    fact_rides
        ride_id, zone_id, driver_id, time_id
        fare, distance_km, duration_minutes, surge_multiplier

    dim_zones:    zone_id, zone_name, borough, area_sq_km
    dim_drivers:  driver_id, driver_name, vehicle_type, rating
    dim_time:     time_id, date, hour, day_of_week, is_weekend, month, quarter

SCD TYPE 2 (Slowly Changing Dimension):
- When a dimension attribute changes (driver gets a new vehicle),
  we don't overwrite — we close the old row and insert a new one.
- Each row has valid_from, valid_to, and is_current flags.
- This preserves history for point-in-time analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Callable


@dataclass
class DimensionRecord:
    """A single record in a dimension table with SCD Type 2 support."""
    key: str
    attributes: dict[str, Any]
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: datetime | None = None
    is_current: bool = True


class DimensionTable:
    """
    A dimension table with SCD Type 2 support.

    Stores descriptive attributes and maintains history
    when attributes change over time.
    """

    def __init__(self, name: str, key_column: str) -> None:
        self.name = name
        self.key_column = key_column
        self._records: list[DimensionRecord] = []

    @property
    def records(self) -> list[DimensionRecord]:
        return list(self._records)

    @property
    def current_records(self) -> list[DimensionRecord]:
        return [r for r in self._records if r.is_current]

    def add(self, key: str, attributes: dict[str, Any]) -> DimensionRecord:
        """Add a new dimension record."""
        record = DimensionRecord(key=key, attributes=dict(attributes))
        self._records.append(record)
        return record

    def lookup(self, key: str) -> DimensionRecord | None:
        """Look up the current version of a dimension record."""
        for record in self._records:
            if record.key == key and record.is_current:
                return record
        return None

    def lookup_as_of(self, key: str, as_of: datetime) -> DimensionRecord | None:
        """Point-in-time lookup: find the version valid at a given timestamp."""
        for record in self._records:
            if record.key != key:
                continue
            if record.valid_from <= as_of:
                if record.valid_to is None or as_of < record.valid_to:
                    return record
        return None

    def scd_type2_update(
        self, key: str, new_attributes: dict[str, Any]
    ) -> tuple[DimensionRecord, DimensionRecord]:
        """
        SCD Type 2 update: close the current record and insert a new version.

        Returns (closed_record, new_record).

        This preserves history. Queries joining on the dimension key
        will get the version that was valid at the time of the fact event.
        """
        current = self.lookup(key)
        if current is None:
            raise KeyError(f"No current record found for key: {key}")

        now = datetime.now()
        # Close the current record
        current.valid_to = now
        current.is_current = False

        # Insert new version with merged attributes
        merged = {**current.attributes, **new_attributes}
        new_record = DimensionRecord(
            key=key, attributes=merged, valid_from=now, is_current=True
        )
        self._records.append(new_record)
        return current, new_record

    def history(self, key: str) -> list[DimensionRecord]:
        """Get all versions of a dimension record, ordered by valid_from."""
        versions = [r for r in self._records if r.key == key]
        return sorted(versions, key=lambda r: r.valid_from)


class FactTable:
    """
    A fact table storing measurable events with foreign keys to dimensions.

    Facts are append-only — we never update a fact record. If a correction
    is needed, we insert a new record (possibly with a negative measure
    for reversals).
    """

    def __init__(self, name: str, dimension_keys: list[str], measures: list[str]) -> None:
        self.name = name
        self.dimension_keys = dimension_keys
        self.measures = measures
        self._facts: list[dict[str, Any]] = []

    @property
    def facts(self) -> list[dict[str, Any]]:
        return list(self._facts)

    @property
    def count(self) -> int:
        return len(self._facts)

    def add_fact(self, record: dict[str, Any]) -> None:
        """
        Add a fact record. Must contain all dimension keys and measures.
        """
        for key in self.dimension_keys:
            if key not in record:
                raise ValueError(f"Missing dimension key: {key}")
        for measure in self.measures:
            if measure not in record:
                raise ValueError(f"Missing measure: {measure}")
        self._facts.append(dict(record))

    def query(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Query facts with optional filters.

        Filters are key-value pairs where the fact record must match.
        """
        if not filters:
            return list(self._facts)

        results = []
        for fact in self._facts:
            if all(fact.get(k) == v for k, v in filters.items()):
                results.append(dict(fact))
        return results

    def aggregate(
        self,
        group_by: list[str],
        metric: str,
        func: str = "sum",
    ) -> list[dict[str, Any]]:
        """
        Aggregate facts by group_by columns using the specified function.

        Supported functions: sum, count, avg, min, max.
        """
        if metric not in self.measures and metric != "*":
            raise ValueError(f"Unknown measure: {metric}")

        # Group records
        groups: dict[tuple, list[float]] = {}
        for fact in self._facts:
            key = tuple(fact.get(g) for g in group_by)
            value = fact.get(metric, 0) if metric != "*" else 1
            groups.setdefault(key, []).append(value)

        # Aggregate
        results = []
        for key, values in groups.items():
            row = {g: k for g, k in zip(group_by, key)}
            if func == "sum":
                row[f"{func}_{metric}"] = sum(values)
            elif func == "count":
                row[f"{func}_{metric}"] = len(values)
            elif func == "avg":
                row[f"{func}_{metric}"] = round(sum(values) / len(values), 4)
            elif func == "min":
                row[f"{func}_{metric}"] = min(values)
            elif func == "max":
                row[f"{func}_{metric}"] = max(values)
            else:
                raise ValueError(f"Unknown function: {func}")
            results.append(row)

        return results


class StarSchema:
    """
    Combines a fact table with dimension tables for denormalized queries.

    In a star schema, the fact table sits at the center with dimension
    tables radiating outward like points of a star. Queries typically:
    1. Filter on dimensions (WHERE zone = 'Manhattan')
    2. Group by dimensions (GROUP BY day_of_week)
    3. Aggregate measures (SUM(fare), AVG(duration))
    """

    def __init__(self, fact_table: FactTable) -> None:
        self.fact_table = fact_table
        self._dimensions: dict[str, DimensionTable] = {}

    def add_dimension(self, fk_column: str, dimension: DimensionTable) -> None:
        """Register a dimension table linked by the foreign key column."""
        self._dimensions[fk_column] = dimension

    def denormalized_query(
        self,
        fact_filters: dict[str, Any] | None = None,
        include_dims: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Join fact records with dimension attributes.

        This simulates the denormalized "wide table" that results
        from joining fact + dimensions. In ClickHouse, you'd use
        dictionaries or JOINs for this.
        """
        facts = self.fact_table.query(fact_filters)
        dims_to_include = include_dims or list(self._dimensions.keys())

        results = []
        for fact in facts:
            row = dict(fact)
            for fk_col in dims_to_include:
                if fk_col in self._dimensions:
                    dim = self._dimensions[fk_col]
                    dim_key = fact.get(fk_col)
                    if dim_key:
                        record = dim.lookup(dim_key)
                        if record:
                            # Prefix dimension attributes to avoid name collisions
                            for attr_name, attr_val in record.attributes.items():
                                row[f"{dim.name}_{attr_name}"] = attr_val
            results.append(row)
        return results
