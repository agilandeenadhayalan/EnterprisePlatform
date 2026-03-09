"""Tests for Module 15: Data Lake Architecture."""

import pytest

from learning.phase_3.src.m15_data_lake.medallion import (
    BronzeLayer,
    SilverLayer,
    GoldLayer,
    MedallionPipeline,
    BronzeRecord,
)
from learning.phase_3.src.m15_data_lake.parquet_io import (
    ParquetSchema,
    ColumnDef,
    ParquetWriter,
    ParquetReader,
    SchemaEvolution,
)
from learning.phase_3.src.m15_data_lake.lakehouse import (
    TableFormat,
    TimeTravel,
    Lakehouse,
)


# ── Medallion ──


class TestBronzeLayer:
    def test_ingest_appends_records(self):
        bronze = BronzeLayer()
        records = bronze.ingest(
            [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}],
            source="api",
        )
        assert bronze.count == 2
        assert len(records) == 2

    def test_bronze_immutability(self):
        bronze = BronzeLayer()
        original_data = {"id": 1, "val": "original"}
        bronze.ingest(original_data, source="api")
        # Modifying the input should not affect stored data
        original_data["val"] = "modified"
        assert bronze.records[0].raw_data["val"] == "original"

    def test_ingest_single_record(self):
        bronze = BronzeLayer()
        records = bronze.ingest({"id": 1}, source="api")
        assert len(records) == 1


class TestSilverLayer:
    def test_removes_null_required_fields(self):
        silver = SilverLayer(required_fields=["id", "fare"])
        bronze_records = [
            BronzeRecord("b1", "api", "2024-01-01", {"id": 1, "fare": 25.0}),
            BronzeRecord("b2", "api", "2024-01-01", {"id": 2, "fare": None}),
        ]
        accepted = silver.transform(bronze_records)
        assert len(accepted) == 1
        assert silver.rejected_count == 1

    def test_deduplicates_by_content(self):
        silver = SilverLayer()
        data = {"id": 1, "fare": 25.0}
        bronze_records = [
            BronzeRecord("b1", "api", "2024-01-01", data),
            BronzeRecord("b2", "api", "2024-01-01", data),
        ]
        accepted = silver.transform(bronze_records)
        assert len(accepted) == 1
        assert silver.dedup_count == 1

    def test_validates_value_ranges(self):
        silver = SilverLayer(required_fields=["fare"])
        bronze_records = [
            BronzeRecord("b1", "api", "2024-01-01", {"fare": 25.0}),
            BronzeRecord("b2", "api", "2024-01-01", {"fare": 999.0}),
        ]
        accepted = silver.transform(
            bronze_records, value_ranges={"fare": (0, 200)}
        )
        assert len(accepted) == 1
        assert silver.rejected_count == 1

    def test_type_conversions(self):
        silver = SilverLayer()
        bronze_records = [
            BronzeRecord("b1", "api", "2024-01-01", {"fare": "25.5"}),
        ]
        accepted = silver.transform(bronze_records, type_conversions={"fare": float})
        assert accepted[0].data["fare"] == 25.5


class TestGoldLayer:
    def test_aggregation(self):
        gold = GoldLayer()
        from learning.phase_3.src.m15_data_lake.medallion import SilverRecord
        silver_records = [
            SilverRecord("s1", "api", "2024-01-01", {"zone": "A", "fare": 10.0}, "fp1"),
            SilverRecord("s2", "api", "2024-01-01", {"zone": "A", "fare": 20.0}, "fp2"),
            SilverRecord("s3", "api", "2024-01-01", {"zone": "B", "fare": 15.0}, "fp3"),
        ]
        results = gold.aggregate(silver_records, group_by=["zone"], metrics={"fare": "sum"})
        a_group = [r for r in results if r.group_key["zone"] == "A"][0]
        assert a_group.metrics["fare"] == 30.0
        assert a_group.record_count == 2


class TestMedallionPipeline:
    def test_full_pipeline(self):
        pipeline = MedallionPipeline(
            required_fields=["id", "fare"],
            type_conversions={"fare": float},
            value_ranges={"fare": (0, 200)},
            group_by=["zone"],
            metrics={"fare": "sum"},
        )
        raw = [
            {"id": 1, "zone": "A", "fare": "25"},
            {"id": 2, "zone": "A", "fare": "30"},
            {"id": 3, "zone": "B", "fare": None},  # rejected
        ]
        stats = pipeline.run(raw, source="test")
        assert stats["bronze_ingested"] == 3
        assert stats["silver_accepted"] == 2
        assert stats["silver_rejected"] == 1


# ── Parquet ──


class TestParquetSchema:
    def test_validate_valid_record(self):
        schema = ParquetSchema([
            ColumnDef("id", "string", nullable=False),
            ColumnDef("fare", "float"),
        ])
        errors = schema.validate_record({"id": "r1", "fare": 25.0})
        assert len(errors) == 0

    def test_validate_null_non_nullable(self):
        schema = ParquetSchema([
            ColumnDef("id", "string", nullable=False),
        ])
        errors = schema.validate_record({"id": None})
        assert len(errors) == 1

    def test_validate_wrong_type(self):
        schema = ParquetSchema([ColumnDef("fare", "float")])
        errors = schema.validate_record({"fare": "not_a_number"})
        assert len(errors) == 1


class TestParquetReadWrite:
    def test_write_and_read(self):
        schema = ParquetSchema([
            ColumnDef("id", "string"),
            ColumnDef("fare", "float"),
        ])
        writer = ParquetWriter(schema, row_group_size=5)
        writer.write([
            {"id": "r1", "fare": 25.0},
            {"id": "r2", "fare": 30.0},
        ])
        reader = ParquetReader(writer)
        results, stats = reader.read()
        assert len(results) == 2

    def test_column_pruning(self):
        schema = ParquetSchema([
            ColumnDef("id", "string"),
            ColumnDef("fare", "float"),
            ColumnDef("zone", "string"),
        ])
        writer = ParquetWriter(schema)
        writer.write([{"id": "r1", "fare": 25.0, "zone": "A"}])
        reader = ParquetReader(writer)
        results, _ = reader.read(columns=["id", "fare"])
        assert "zone" not in results[0]


class TestSchemaEvolution:
    def test_add_column(self):
        schema = ParquetSchema([ColumnDef("id", "string")])
        new_schema = SchemaEvolution.add_column(schema, ColumnDef("tip", "float"))
        assert len(new_schema.columns) == 2

    def test_backward_compatible_add_nullable(self):
        old = ParquetSchema([ColumnDef("id", "string")])
        new = ParquetSchema([ColumnDef("id", "string"), ColumnDef("tip", "float", nullable=True)])
        compatible, issues = SchemaEvolution.is_backward_compatible(old, new)
        assert compatible is True

    def test_backward_incompatible_add_non_nullable(self):
        old = ParquetSchema([ColumnDef("id", "string")])
        new = ParquetSchema([ColumnDef("id", "string"), ColumnDef("tip", "float", nullable=False)])
        compatible, issues = SchemaEvolution.is_backward_compatible(old, new)
        assert compatible is False

    def test_type_widening(self):
        assert SchemaEvolution.can_widen("int", "float") is True
        assert SchemaEvolution.can_widen("float", "int") is False


# ── Lakehouse ──


class TestTimeTravel:
    def test_as_of_version(self):
        table = TableFormat("test")
        table.append([{"id": 1, "val": "a"}])
        table.append([{"id": 2, "val": "b"}])
        tt = TimeTravel(table)
        v1 = tt.as_of_version(1)
        assert len(v1) == 1
        v2 = tt.as_of_version(2)
        assert len(v2) == 2

    def test_diff_shows_changes(self):
        table = TableFormat("test")
        table.append([{"id": 1, "val": "a"}])
        table.append([{"id": 2, "val": "b"}])
        table.delete({"id": 1})
        tt = TimeTravel(table)
        diff = tt.diff(1, 3)
        assert len(diff["added"]) == 1  # id=2 was added
        assert len(diff["removed"]) == 1  # id=1 was removed

    def test_invalid_version_raises(self):
        table = TableFormat("test")
        table.append([{"id": 1}])
        tt = TimeTravel(table)
        with pytest.raises(ValueError, match="not found"):
            tt.as_of_version(99)

    def test_history_tracks_operations(self):
        table = TableFormat("test")
        table.append([{"id": 1}])
        table.delete({"id": 1})
        tt = TimeTravel(table)
        history = tt.history
        assert len(history) == 2
        assert history[0]["operation"] == "append"
        assert history[1]["operation"] == "delete"
