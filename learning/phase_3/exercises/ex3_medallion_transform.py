"""
Exercise 3: Bronze-to-Silver Transformer
==========================================

The data lake module demonstrated the medallion architecture.
Now implement the Bronze-to-Silver transformation step.

TASK:
Given raw Bronze records, produce cleaned Silver records by:
1. Removing records with null required fields.
2. Standardizing data types (string numbers to floats).
3. Deduplicating by primary key (keep first occurrence).
4. Validating value ranges.

WHY Silver layer:
- Bronze stores raw, dirty data for auditability.
- Silver is the "single source of truth" for analytics.
- Downstream consumers trust Silver data quality.
"""


class BronzeToSilverTransformer:
    """
    TODO: Implement Bronze-to-Silver data cleaning.

    The transformer should:
    1. Remove records with null required fields
    2. Standardize data types (strings to numbers where specified)
    3. Deduplicate by primary key (keep first occurrence)
    4. Validate value ranges (reject out-of-range records)
    """

    def __init__(
        self,
        required_fields: list[str],
        primary_key: str,
        type_conversions: dict[str, type] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """
        Initialize the transformer.

        Args:
            required_fields: Fields that must be non-null.
            primary_key: Field used for deduplication.
            type_conversions: Mapping of field -> target type (e.g., {"fare": float}).
            value_ranges: Mapping of field -> (min, max) for validation.
        """
        self.required_fields = required_fields
        self.primary_key = primary_key
        self.type_conversions = type_conversions or {}
        self.value_ranges = value_ranges or {}
        # TODO: Initialize tracking variables (~3 lines)
        raise NotImplementedError("Initialize transformer")

    def transform(self, records: list[dict]) -> list[dict]:
        """
        Transform a batch of Bronze records into Silver records.

        For each record:
        1. Check required fields (skip if any is None or missing).
        2. Apply type conversions (skip on conversion failure).
        3. Validate value ranges (skip if out of range).
        4. Check for duplicates by primary key (skip duplicates).

        Returns the list of accepted (cleaned) records.

        Track counts of: rejected_nulls, rejected_types,
        rejected_ranges, rejected_duplicates.
        """
        # TODO: Implement (~25 lines)
        raise NotImplementedError("Transform records")

    @property
    def stats(self) -> dict[str, int]:
        """Return transformation statistics."""
        # TODO: Return a dict with accepted, rejected_nulls,
        # rejected_types, rejected_ranges, rejected_duplicates (~5 lines)
        raise NotImplementedError("Return stats")


# ── Verification ──


def test_removes_null_required():
    t = BronzeToSilverTransformer(
        required_fields=["id", "fare"],
        primary_key="id",
    )
    result = t.transform([
        {"id": 1, "fare": 25.0},
        {"id": 2, "fare": None},
    ])
    assert len(result) == 1
    assert t.stats["rejected_nulls"] == 1


def test_type_conversion():
    t = BronzeToSilverTransformer(
        required_fields=["id"],
        primary_key="id",
        type_conversions={"fare": float},
    )
    result = t.transform([{"id": 1, "fare": "25.5"}])
    assert result[0]["fare"] == 25.5


def test_deduplication():
    t = BronzeToSilverTransformer(
        required_fields=["id"],
        primary_key="id",
    )
    result = t.transform([
        {"id": 1, "val": "first"},
        {"id": 1, "val": "duplicate"},
    ])
    assert len(result) == 1
    assert result[0]["val"] == "first"


def test_value_range_validation():
    t = BronzeToSilverTransformer(
        required_fields=["id", "fare"],
        primary_key="id",
        value_ranges={"fare": (0, 200)},
    )
    result = t.transform([
        {"id": 1, "fare": 25.0},
        {"id": 2, "fare": 999.0},
    ])
    assert len(result) == 1


if __name__ == "__main__":
    try:
        test_removes_null_required()
        test_type_conversion()
        test_deduplication()
        test_value_range_validation()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
