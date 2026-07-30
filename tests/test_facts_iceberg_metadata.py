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


def _files(*ids):
    """Data files de 1 byte, um por `sort_order_id`. `None` = coluna ausente
    no dump (o coletor nao trouxe `sort_order_id` para aquele arquivo)."""
    out = []
    for i, order_id in enumerate(ids):
        entry = {"file_path": f"s3://b/t/f{i}.parquet", "file_size_in_bytes": 1}
        if order_id is not None:
            entry["sort_order_id"] = order_id
        out.append(entry)
    return out


class TestWrittenBeforeSortOrder:
    """`attrs.written_before_sort_order` de `iceberg.files_summary` -- o atributo
    que SF-ICE-004 exige. Derivado de `data_file.sort_order_id` (campo 140 da
    spec, presente desde o formato v1) comparado com `default-sort-order-id` da
    tabela. Ver docstring do modulo: `sort_order_id == 0` NAO e evidencia de
    arquivo nao ordenado, porque o writer do Spark so passou a gravar esse
    campo no Iceberg 1.11.0 -- depois de todo runtime Glue existente."""

    def test_attribute_absent_when_default_sort_order_id_not_collected(self):
        fact = one("iceberg.files_summary", {"table": "db.t", "files": _files(0, 0)})
        assert "written_before_sort_order" not in fact.attrs

    def test_table_that_never_had_a_sort_order_asserts_false(self):
        payload = {"table": "db.t", "default_sort_order_id": 0, "files": _files(0, 0, 0)}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is False
        assert fact.measures["files_written_before_sort_order"] == 0

    def test_sort_order_defined_before_any_write_asserts_false(self):
        payload = {"table": "db.t", "default_sort_order_id": 1, "files": _files(1, 1, 1)}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is False
        assert fact.measures["files_written_before_sort_order"] == 0
        assert fact.measures["files_current_sort_order"] == 3

    def test_sort_order_defined_midway_counts_only_the_older_files(self):
        payload = {"table": "db.t", "default_sort_order_id": 2, "files": _files(1, 1, 2, 2, 2)}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is True
        assert fact.measures["files_written_before_sort_order"] == 2
        assert fact.measures["files_stale_sort_order"] == 2
        assert fact.measures["files_current_sort_order"] == 3
        assert fact.measures["files_sort_order_unknown"] == 0

    def test_zero_never_asserts_true_because_glue_always_writes_zero(self):
        """A armadilha central. Ate Iceberg 1.10.0 -- ou seja, em Glue 4.0, 5.0
        e 5.1 -- `SparkWrite` nunca chama `dataSortOrder`, entao TODO data file
        escrito pelo Spark carrega `sort_order_id = 0`, inclusive logo depois
        de um `rewrite_data_files` com estrategia sort. Ler esse 0 como
        "arquivo nao ordenado" faria a regra disparar em toda tabela Iceberg
        de Glue, mandando rodar rewrite em tabelas que acabaram de ser
        compactadas."""
        payload = {"table": "db.t", "default_sort_order_id": 2, "files": _files(0, 0, 0, 0)}
        fact = one("iceberg.files_summary", payload)
        assert "written_before_sort_order" not in fact.attrs
        assert fact.measures["files_sort_order_unknown"] == 4
        assert fact.measures["files_stale_sort_order"] == 0

    def test_zero_is_indistinguishable_from_a_missing_column(self):
        explicit_zero = one(
            "iceberg.files_summary",
            {"table": "db.t", "default_sort_order_id": 2, "files": _files(0, 0)},
        )
        no_column = one(
            "iceberg.files_summary",
            {"table": "db.t", "default_sort_order_id": 2, "files": _files(None, None)},
        )
        assert explicit_zero.measures["files_sort_order_unknown"] == 2
        assert no_column.measures["files_sort_order_unknown"] == 2
        assert explicit_zero.attrs == no_column.attrs == {}

    def test_file_under_a_previous_non_zero_order_predates_the_current(self):
        payload = {"table": "db.t", "default_sort_order_id": 3, "files": _files(1, 3)}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is True
        assert fact.measures["files_stale_sort_order"] == 1
        assert fact.measures["files_written_before_sort_order"] == 1

    def test_empty_table_with_sort_order_asserts_false(self):
        payload = {"table": "db.t", "default_sort_order_id": 1, "files": []}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is False

    def test_missing_sort_order_id_leaves_the_attribute_unset(self):
        """Sem `sort_order_id` por arquivo a pergunta e inrespondivel. A spec diz
        "assumed to be unsorted"; assumir aqui mandaria alguem rodar
        rewrite_data_files numa tabela grande sem evidencia."""
        payload = {"table": "db.t", "default_sort_order_id": 1, "files": _files(None, None)}
        fact = one("iceberg.files_summary", payload)
        assert "written_before_sort_order" not in fact.attrs
        assert fact.measures["files_sort_order_unknown"] == 2
        # Sem veredito, nao ha total: um zero aqui se leria como "nenhum
        # arquivo antigo", que e exatamente o que nao se sabe.
        assert "files_written_before_sort_order" not in fact.measures

    def test_missing_sort_order_id_is_counted_as_unresolved(self):
        payload = {"table": "db.t", "default_sort_order_id": 1, "files": _files(None, None)}
        facts = extract_iceberg_metadata(payload, "dump.json")
        unresolved = facts_of("iceberg.unresolved", facts)
        assert [u.attrs["reason"] for u in unresolved] == ["sort_order_id_missing"]
        assert unresolved[0].attrs["file_count"] == 2
        analyzed = facts_of("iceberg.table_analyzed", facts)[0]
        assert analyzed.measures["unresolved_count"] == 1

    def test_one_confirmed_old_file_wins_over_unknown_ones(self):
        """Um arquivo comprovadamente sob outra ordem registrada ja prova o
        passivo; os desconhecidos so nao entram na contagem, que passa a ser um
        piso confirmado em vez de um total."""
        payload = {"table": "db.t", "default_sort_order_id": 2, "files": _files(1, None, 2)}
        fact = one("iceberg.files_summary", payload)
        assert fact.attrs["written_before_sort_order"] is True
        assert fact.measures["files_written_before_sort_order"] == 1
        assert fact.measures["files_sort_order_unknown"] == 1

    def test_unknown_files_block_the_false_assertion(self):
        payload = {"table": "db.t", "default_sort_order_id": 1, "files": _files(1, None)}
        fact = one("iceberg.files_summary", payload)
        assert "written_before_sort_order" not in fact.attrs

    def test_malformed_default_sort_order_id_is_unresolved_not_a_guess(self):
        payload = {"table": "db.t", "default_sort_order_id": "1", "files": _files(1)}
        facts = extract_iceberg_metadata(payload, "dump.json")
        summary = facts_of("iceberg.files_summary", facts)[0]
        assert "written_before_sort_order" not in summary.attrs
        unresolved = facts_of("iceberg.unresolved", facts)
        assert [u.attrs["reason"] for u in unresolved] == ["malformed_json"]
        assert unresolved[0].attrs["section"] == "default_sort_order_id"

    def test_non_int_sort_order_id_on_a_file_counts_as_unknown(self):
        payload = {
            "table": "db.t",
            "default_sort_order_id": 1,
            "files": [{"file_size_in_bytes": 1, "sort_order_id": "zero"}],
        }
        fact = one("iceberg.files_summary", payload)
        assert fact.measures["files_sort_order_unknown"] == 1
        assert "written_before_sort_order" not in fact.attrs

    def test_boolean_sort_order_id_is_not_read_as_int_zero(self):
        """`False` e `int` em Python. Sem a guarda de bool, um `sort_order_id:
        false` viraria "arquivo nao ordenado" e a regra dispararia por lixo."""
        payload = {
            "table": "db.t",
            "default_sort_order_id": 1,
            "files": [{"file_size_in_bytes": 1, "sort_order_id": False}],
        }
        fact = one("iceberg.files_summary", payload)
        assert fact.measures["files_sort_order_unknown"] == 1
        assert "written_before_sort_order" not in fact.attrs

    def test_metadata_log_section_never_produces_the_attribute(self):
        """A spec define cada entrada de `metadata-log` como apenas
        `metadata-file` + `timestamp-ms`: nao ha sort order nela, entao um dump
        unico nao consegue datar a mudanca de sort order por esse caminho."""
        payload = {
            "table": "db.t",
            "files": _files(1, 1),
            "metadata_log": [
                {"metadata-file": "s3://b/t/metadata/v1.json", "timestamp-ms": 1515100},
                {"metadata-file": "s3://b/t/metadata/v2.json", "timestamp-ms": 1515200},
            ],
        }
        fact = one("iceberg.files_summary", payload)
        assert "written_before_sort_order" not in fact.attrs

    def test_files_section_absent_produces_no_summary_at_all(self):
        facts = extract_iceberg_metadata(
            {"table": "db.t", "default_sort_order_id": 1}, "dump.json"
        )
        assert not facts_of("iceberg.files_summary", facts)
        assert not facts_of("iceberg.unresolved", facts)

    def test_every_fact_validates_against_the_schema(self):
        payload = {"table": "db.t", "default_sort_order_id": 2, "files": _files(1, None, 2)}
        for fact in extract_iceberg_metadata(payload, "dump.json"):
            validate_fact(fact.to_dict())


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
