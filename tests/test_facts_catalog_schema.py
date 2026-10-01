from sparkforge.facts.catalog_schema import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    extract_catalog_schema,
)
from sparkforge.findings.validate import validate_fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

EXPECTED_KINDS = {
    "catalog.table_schema",
    "catalog.table_partitions",
    "catalog.table_property",
    "catalog.table_property.projection_enabled",
    "catalog.unresolved",
    "catalog.analyzed",
}


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def one(kind, payload, path="catalog.json"):
    got = facts_of(kind, extract_catalog_schema(payload, path))
    assert got, f"nenhum fact {kind}"
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 6
    assert EXTRACTOR_ID.startswith("catalog_schema@")


FULL_TABLE = {
    "name": "db.eventos",
    "storage_format": "parquet",
    "partition_keys": [{"name": "dt", "type": "string"}],
    "columns": [
        {"name": "cliente_id", "type": "bigint"},
        {"name": "valor", "type": "double"},
    ],
    "properties": {"projection.enabled": "true"},
    "partition_count": 1200,
}


class TestTableSchema:
    def test_full_table_produces_expected_attrs(self):
        fact = one("catalog.table_schema", {"tables": [FULL_TABLE]})
        assert fact.attrs["table"] == "db.eventos"
        assert fact.attrs["storage_format"] == "parquet"
        assert fact.attrs["columnar"] is True
        assert fact.attrs["partition_keys"] == ["dt"]
        assert fact.measures["column_count"] == 2
        assert fact.measures["partition_key_count"] == 1

    def test_column_types_merges_columns_and_partition_keys(self):
        fact = one("catalog.table_schema", {"tables": [FULL_TABLE]})
        assert fact.attrs["column_types"] == {
            "cliente_id": "bigint",
            "valor": "double",
            "dt": "string",
        }

    def test_columns_entry_wins_over_partition_keys_entry(self):
        table = {
            "name": "db.t",
            "columns": [{"name": "dt", "type": "date"}],
            "partition_keys": [{"name": "dt", "type": "string"}],
        }
        fact = one("catalog.table_schema", {"tables": [table]})
        assert fact.attrs["column_types"]["dt"] == "date"

    def test_csv_storage_is_not_columnar(self):
        table = {"name": "db.t", "storage_format": "csv"}
        fact = one("catalog.table_schema", {"tables": [table]})
        assert fact.attrs["columnar"] is False

    def test_orc_is_columnar(self):
        table = {"name": "db.t", "storage_format": "orc"}
        fact = one("catalog.table_schema", {"tables": [table]})
        assert fact.attrs["columnar"] is True

    def test_minimal_table_tolerates_missing_keys(self):
        """`{name, columns}` -- o minimo que o enunciado exige que funcione."""
        fact = one("catalog.table_schema", {"tables": [{"name": "db.t", "columns": []}]})
        assert fact.attrs["table"] == "db.t"
        assert fact.attrs["storage_format"] is None
        assert fact.attrs["columnar"] is None
        assert fact.attrs["partition_keys"] == []
        assert fact.measures["column_count"] == 0
        assert "partition_key_count" not in fact.measures

    def test_missing_table_name_is_unresolved(self):
        facts = extract_catalog_schema({"tables": [{"columns": []}]}, "c.json")
        unresolved = facts_of("catalog.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "missing_table_name"
        assert not facts_of("catalog.table_schema", facts)

    def test_subject_is_a_table_subject(self):
        fact = one("catalog.table_schema", {"tables": [FULL_TABLE]})
        assert fact.subject["type"] == "table"
        assert fact.subject["symbol"] == "db.eventos"


class TestTablePartitions:
    def test_partition_count_present(self):
        fact = one("catalog.table_partitions", {"tables": [FULL_TABLE]})
        assert fact.measures["partition_count"] == 1200
        assert fact.measures["distinct_values"] == 1200
        assert "avg_bytes_per_partition" not in fact.measures

    def test_avg_bytes_derivable_with_total_size(self):
        table = {"name": "db.t", "partition_count": 10, "total_size_bytes": 1000}
        fact = one("catalog.table_partitions", {"tables": [table]})
        assert fact.measures["avg_bytes_per_partition"] == 100.0

    def test_no_partition_count_means_no_fact(self):
        facts = extract_catalog_schema({"tables": [{"name": "db.t"}]}, "c.json")
        assert facts_of("catalog.table_partitions", facts) == []


class TestTableProperty:
    def test_generic_property_fact_emitted(self):
        fact = one("catalog.table_property", {"tables": [FULL_TABLE]})
        assert fact.attrs["key"] == "projection.enabled"
        assert fact.attrs["value"] == "true"
        assert fact.attrs["present"] is True

    def test_projection_enabled_truthy_emits_special_kind(self):
        fact = one("catalog.table_property.projection_enabled", {"tables": [FULL_TABLE]})
        assert fact.attrs["key"] == "projection.enabled"

    def test_projection_enabled_falsy_does_not_emit_special_kind(self):
        table = {"name": "db.t", "properties": {"projection.enabled": "false"}}
        facts = extract_catalog_schema({"tables": [table]}, "c.json")
        assert facts_of("catalog.table_property.projection_enabled", facts) == []
        assert facts_of("catalog.table_property", facts)

    def test_no_properties_means_no_property_facts(self):
        facts = extract_catalog_schema({"tables": [{"name": "db.t"}]}, "c.json")
        assert facts_of("catalog.table_property", facts) == []


class TestSentinel:
    def test_counts_reflect_tables_and_unresolved(self):
        payload = {"tables": [FULL_TABLE, {"columns": []}]}
        fact = one("catalog.analyzed", payload)
        assert fact.measures["table_count"] == 1
        assert fact.measures["unresolved_count"] == 1

    def test_missing_tables_key_still_produces_sentinel(self):
        facts = extract_catalog_schema({}, "c.json")
        assert facts_of("catalog.analyzed", facts)
        assert facts_of("catalog.table_schema", facts) == []

    def test_tables_not_a_list_is_malformed(self):
        facts = extract_catalog_schema({"tables": "nope"}, "c.json")
        unresolved = facts_of("catalog.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "malformed_json"

    def test_payload_not_a_dict_is_malformed(self):
        facts = extract_catalog_schema([], "c.json")
        unresolved = facts_of("catalog.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "malformed_json"


class TestUnblocksSfAth003:
    """SF-ATH-003 (rules/catalog/athena.yaml) nunca esteve `blocked_on` -- so
    faltava o fact `catalog.table_partitions`, que este extrator produz.
    Nao e parte do trabalho de fusao (`fusion.py`), mas e um efeito colateral
    direto de dar o shape certo a este fact; ver docstring de
    `sparkforge/facts/catalog_schema.py`."""

    def test_fires_when_partition_count_exceeds_threshold_without_projection(self):
        payload = {
            "tables": [
                {"name": "db.eventos", "storage_format": "parquet", "partition_count": 150000}
            ]
        }
        facts = extract_catalog_schema(payload, "c.json")
        findings = judge(facts, load_catalog(), {"athena": "*"})
        assert "SF-ATH-003" in {f.rule_id for f in findings}

    def test_does_not_fire_when_projection_enabled(self):
        payload = {
            "tables": [
                {
                    "name": "db.eventos",
                    "storage_format": "parquet",
                    "partition_count": 150000,
                    "properties": {"projection.enabled": "true"},
                }
            ]
        }
        facts = extract_catalog_schema(payload, "c.json")
        findings = judge(facts, load_catalog(), {"athena": "*"})
        assert "SF-ATH-003" not in {f.rule_id for f in findings}


class TestSchemaValidity:
    def test_every_fact_validates(self):
        for fact in extract_catalog_schema({"tables": [FULL_TABLE]}, "c.json"):
            validate_fact(fact.to_dict())

    def test_kind_namespace_never_leaks_unknown_kind(self):
        facts = extract_catalog_schema({"tables": [FULL_TABLE]}, "c.json")
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_extraction_is_deterministic(self):
        payload = {"tables": [FULL_TABLE]}
        first = [f.to_dict() for f in extract_catalog_schema(payload, "c.json")]
        second = [f.to_dict() for f in extract_catalog_schema(payload, "c.json")]
        assert first == second
