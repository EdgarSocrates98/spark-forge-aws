from sparkforge.facts.iceberg_metadata import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    extract_iceberg_metadata,
)
from sparkforge.findings.validate import validate_fact

EXPECTED_KINDS = {
    "iceberg.files_summary",
    "iceberg.delete_files_summary",
    "iceberg.snapshots_summary",
    "iceberg.manifests_summary",
    "iceberg.partitions_summary",
    "iceberg.table_property",
    "iceberg.unresolved",
    "iceberg.table_analyzed",
}


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def one(kind, payload, path="dump.json"):
    got = facts_of(kind, extract_iceberg_metadata(payload, path))
    assert got, f"nenhum fact {kind}"
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 8
    assert EXTRACTOR_ID.startswith("iceberg_metadata@")


class TestMissingTableName:
    def test_no_table_key_is_unresolved(self):
        facts = extract_iceberg_metadata({"files": []}, "dump.json")
        assert len(facts) == 1
        assert facts[0].kind == "iceberg.unresolved"
        assert facts[0].attrs["reason"] == "missing_table_name"

    def test_blank_table_name_is_unresolved(self):
        facts = extract_iceberg_metadata({"table": "   "}, "dump.json")
        assert facts[0].attrs["reason"] == "missing_table_name"

    def test_non_dict_payload_is_malformed(self):
        facts = extract_iceberg_metadata(["not", "a", "dict"], "dump.json")  # type: ignore[arg-type]
        assert facts[0].attrs["reason"] == "malformed_json"


class TestFilesSummary:
    def test_missing_files_section_emits_nothing(self):
        facts = extract_iceberg_metadata({"table": "db.t"}, "dump.json")
        assert not facts_of("iceberg.files_summary", facts)
        analyzed = one("iceberg.table_analyzed", {"table": "db.t"})
        assert analyzed.measures["section_count"] == 0

    def test_empty_files_list_is_a_real_zero_not_missing(self):
        fact = one("iceberg.files_summary", {"table": "db.t", "files": []})
        assert fact.measures["data_file_count"] == 0
        assert "avg_file_bytes" not in fact.measures

    def test_percentiles_and_totals(self):
        payload = {
            "table": "db.t",
            "files": [{"file_size_in_bytes": size} for size in (100, 200, 300, 400)],
        }
        fact = one("iceberg.files_summary", payload)
        assert fact.measures["data_file_count"] == 4
        assert fact.measures["total_bytes"] == 1000
        assert fact.measures["avg_file_bytes"] == 250
        assert fact.measures["min_file_bytes"] == 100
        assert fact.measures["max_file_bytes"] == 400

    def test_single_file_percentile_never_divides_by_zero(self):
        payload = {"table": "db.t", "files": [{"file_size_in_bytes": 42}]}
        fact = one("iceberg.files_summary", payload)
        assert fact.measures["p50_file_bytes"] == 42
        assert fact.measures["p95_file_bytes"] == 42

    def test_malformed_files_section_is_unresolved(self):
        facts = extract_iceberg_metadata({"table": "db.t", "files": "not-a-list"}, "dump.json")
        unresolved = facts_of("iceberg.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "malformed_json"
        assert unresolved[0].attrs["section"] == "files"


class TestDeleteFilesSummary:
    def test_data_file_count_present_when_files_section_also_present(self):
        payload = {
            "table": "db.t",
            "files": [{"file_size_in_bytes": 1}, {"file_size_in_bytes": 1}],
            "delete_files": [{"file_size_in_bytes": 1}],
        }
        fact = one("iceberg.delete_files_summary", payload)
        assert fact.measures["delete_file_count"] == 1
        assert fact.measures["data_file_count"] == 2

    def test_data_file_count_omitted_never_fabricated_when_files_absent(self):
        payload = {"table": "db.t", "delete_files": [{"file_size_in_bytes": 1}]}
        fact = one("iceberg.delete_files_summary", payload)
        assert "data_file_count" not in fact.measures


class TestSnapshotsSummary:
    def test_span_hours_and_operations(self):
        payload = {
            "table": "db.t",
            "snapshots": [
                {"snapshot_id": 1, "committed_at": "2026-01-01T00:00:00Z", "operation": "append"},
                {"snapshot_id": 2, "committed_at": "2026-01-02T00:00:00Z", "operation": "delete"},
            ],
        }
        fact = one("iceberg.snapshots_summary", payload)
        assert fact.measures["snapshot_count"] == 2
        assert fact.measures["span_hours"] == 24.0
        assert fact.attrs["operations"] == ["append", "delete"]

    def test_unparseable_timestamps_omit_span_without_crashing(self):
        payload = {"table": "db.t", "snapshots": [{"snapshot_id": 1, "committed_at": "not-a-date"}]}
        fact = one("iceberg.snapshots_summary", payload)
        assert fact.measures["snapshot_count"] == 1
        assert "span_hours" not in fact.measures


class TestTableProperty:
    def test_property_key_value_present(self):
        payload = {"table": "db.t", "properties": {"format-version": "2"}}
        fact = one("iceberg.table_property", payload)
        assert fact.attrs == {
            "key": "format-version",
            "value": "2",
            "present": True,
            "non_empty": True,
        }

    def test_sort_order_present_when_non_empty(self):
        payload = {"table": "db.t", "sort_order": [{"column": "id"}]}
        fact = one("iceberg.table_property", payload)
        assert fact.attrs == {"key": "sort-order", "present": True, "non_empty": True}

    def test_sort_order_not_present_when_declared_empty(self):
        payload = {"table": "db.t", "sort_order": []}
        fact = one("iceberg.table_property", payload)
        assert fact.attrs["present"] is False

    def test_partition_spec_non_empty(self):
        payload = {"table": "db.t", "partition_spec": [{"name": "dt"}]}
        fact = one("iceberg.table_property", payload)
        assert fact.attrs["key"] == "partition-spec"
        assert fact.attrs["non_empty"] is True


class TestSentinel:
    def test_section_count_reflects_sections_present(self):
        payload = {
            "table": "db.t",
            "files": [],
            "properties": {"a": "b"},
        }
        fact = one("iceberg.table_analyzed", payload)
        assert fact.measures["section_count"] == 2
        assert fact.measures["unresolved_count"] == 0

    def test_unresolved_count_reflects_malformed_sections(self):
        payload = {"table": "db.t", "files": "not-a-list", "delete_files": "also-not-a-list"}
        fact = one("iceberg.table_analyzed", payload)
        assert fact.measures["unresolved_count"] == 2


class TestSchemaValidity:
    def test_every_fact_from_a_rich_payload_validates(self):
        payload = {
            "table": "db.t",
            "properties": {"write.distribution-mode": "none", "format-version": "3"},
            "files": [{"file_size_in_bytes": 100, "record_count": 1}],
            "delete_files": [{"file_size_in_bytes": 10}],
            "snapshots": [
                {"snapshot_id": 1, "committed_at": "2026-01-01T00:00:00Z", "operation": "append"}
            ],
            "manifests": [{"length": 10, "added_data_files_count": 1}],
            "partitions": [{"file_count": 1, "record_count": 1}],
            "sort_order": [{"column": "id"}],
            "partition_spec": [{"name": "dt"}],
        }
        for fact in extract_iceberg_metadata(payload, "dump.json"):
            validate_fact(fact.to_dict())

    def test_kind_namespace_never_leaks_unknown_kind(self):
        payload = {
            "table": "db.t",
            "files": [],
            "delete_files": [],
            "snapshots": [],
            "manifests": [],
            "partitions": [],
        }
        facts = extract_iceberg_metadata(payload, "dump.json")
        assert {f.kind for f in facts} <= EMITTED_KINDS
