from sparkforge.facts.catalog_schema import extract_catalog_schema
from sparkforge.facts.fusion import EMITTED_KINDS, EXTRACTOR_ID, fuse
from sparkforge.facts.sql_literal import extract_sql
from sparkforge.findings.validate import validate_fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

EXPECTED_KINDS = {
    "sql.projection.enriched",
    "sql.predicate.enriched",
    "sql.predicate.partition_filter",
    "fusion.summary",
}


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def one(kind, facts):
    got = facts_of(kind, facts)
    assert got, f"nenhum fact {kind}"
    return got[0]


def _catalog(tables):
    return extract_catalog_schema({"tables": tables}, "catalog.json")


PARQUET_EVENTOS = {
    "name": "db.eventos",
    "storage_format": "parquet",
    "partition_keys": [{"name": "dt", "type": "string"}],
    "columns": [{"name": "cliente_id", "type": "bigint"}, {"name": "dt", "type": "string"}],
}


def test_kind_namespace_is_complete_and_documented():
    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 4
    assert EXTRACTOR_ID.startswith("fusion@")


class TestProjectionEnrichment:
    def test_select_star_parquet_resolves_columnar_true(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)

        enriched = one("sql.projection.enriched", fused)
        assert enriched.attrs["star"] is True
        assert enriched.attrs["table_format_columnar"] is True
        assert len(enriched.attrs["fused_from"]) == 2

    def test_csv_table_resolves_columnar_false(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([{"name": "db.eventos", "storage_format": "csv"}])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.projection.enriched", fused)
        assert enriched.attrs["table_format_columnar"] is False

    def test_unmatched_table_produces_no_enriched_fact(self):
        sql_facts = extract_sql("SELECT * FROM db.outra_tabela", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        assert facts_of("sql.projection.enriched", fused) == []
        summary = one("fusion.summary", fused)
        assert summary.measures["unmatched_projection_count"] == 1

    def test_bare_name_matches_unambiguous_catalog_table(self):
        sql_facts = extract_sql("SELECT * FROM eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.projection.enriched", fused)
        assert enriched.attrs["table_format_columnar"] is True

    def test_bare_name_ambiguous_across_two_catalog_tables_is_not_fused(self):
        sql_facts = extract_sql("SELECT * FROM eventos", "q.sql")
        catalog_facts = _catalog(
            [
                {"name": "vendas.eventos", "storage_format": "parquet"},
                {"name": "analytics.eventos", "storage_format": "parquet"},
            ]
        )
        fused = fuse(sql_facts + catalog_facts)
        assert facts_of("sql.projection.enriched", fused) == []
        summary = one("fusion.summary", fused)
        assert summary.measures["unmatched_projection_count"] == 1
        assert summary.measures["tables_known"] == 2


class TestPredicateEnrichment:
    def test_partition_column_filter_is_confirmed(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE dt = '2026-01-01'", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)

        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["on_partition_column"] is True
        assert facts_of("sql.predicate.partition_filter", fused)

    def test_non_partition_column_filter_is_not_a_partition_filter(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE cliente_id = 1", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)

        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["on_partition_column"] is False
        assert facts_of("sql.predicate.partition_filter", fused) == []

    def test_string_literal_against_numeric_column_is_a_mismatch(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE cliente_id = '123'", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["type_mismatch"] is True

    def test_numeric_literal_against_string_column_is_a_mismatch(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE dt = 20260101", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["type_mismatch"] is True

    def test_string_literal_against_string_column_is_not_a_mismatch(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE dt = '2026-01-01'", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["type_mismatch"] is False

    def test_unknown_column_type_leaves_type_mismatch_none(self):
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE nao_existe = '1'", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["type_mismatch"] is None

    def test_ambiguous_literal_shape_leaves_type_mismatch_none(self):
        """`TRUE` nao e claramente string nem numero -- nao adivinha."""
        table = {"name": "db.eventos", "columns": [{"name": "ativo", "type": "boolean"}]}
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE ativo = TRUE", "q.sql")
        catalog_facts = _catalog([table])
        fused = fuse(sql_facts + catalog_facts)
        enriched = one("sql.predicate.enriched", fused)
        assert enriched.attrs["type_mismatch"] is None

    def test_unmatched_predicate_table_is_counted(self):
        sql_facts = extract_sql("SELECT a FROM db.outra WHERE x = 1", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        assert facts_of("sql.predicate.enriched", fused) == []
        summary = one("fusion.summary", fused)
        assert summary.measures["unmatched_predicate_count"] == 1


class TestFusionSummary:
    def test_reflects_tables_known(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        summary = one("fusion.summary", fused)
        assert summary.measures["tables_known"] == 1
        assert summary.measures["enriched_count"] == 1

    def test_no_catalog_at_all_still_produces_summary(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        fused = fuse(sql_facts)
        summary = one("fusion.summary", fused)
        assert summary.measures["tables_known"] == 0
        assert summary.measures["unmatched_projection_count"] == 1


class TestIdempotent:
    def test_second_fuse_adds_no_enriched_facts(self):
        sql_facts = extract_sql(
            "SELECT a FROM db.eventos WHERE dt = '2026-01-01'", "q.sql"
        )
        catalog_facts = _catalog([PARQUET_EVENTOS])
        once = fuse(sql_facts + catalog_facts)
        twice = fuse(once)
        as_dicts = lambda facts: sorted(  # noqa: E731
            (f.to_dict() for f in facts), key=lambda d: (d["kind"], d["id"])
        )
        assert as_dicts(once) == as_dicts(twice)

    def test_enriched_fact_count_stable_across_repeated_fuse(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        once = fuse(sql_facts + catalog_facts)
        twice = fuse(once)
        assert len(facts_of("sql.projection.enriched", once)) == 1
        assert len(facts_of("sql.projection.enriched", twice)) == 1


class TestSchemaValidity:
    def test_every_fact_validates(self):
        sql_facts = extract_sql(
            "SELECT a FROM db.eventos WHERE dt = '2026-01-01'", "q.sql"
        )
        catalog_facts = _catalog([PARQUET_EVENTOS])
        for fact in fuse(sql_facts + catalog_facts):
            validate_fact(fact.to_dict())

    def test_kind_namespace_never_leaks_unknown_kind(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        new_kinds = {f.kind for f in fused} - {f.kind for f in sql_facts + catalog_facts}
        assert new_kinds <= EMITTED_KINDS


class TestEndToEndProbes:
    """Prova de fogo: SF-ATH-001/002/005 disparando a partir de facts fundidos."""

    def test_sf_ath_001_fires_on_select_star_parquet(self):
        sql_facts = extract_sql("SELECT * FROM db.eventos", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        runtime = {"athena": "*"}
        findings = judge(fused, load_catalog(), runtime)
        assert "SF-ATH-001" in {f.rule_id for f in findings}

    def test_sf_ath_002_fires_on_limit_without_any_filter(self):
        sql_facts = extract_sql("SELECT a, b FROM db.eventos LIMIT 10", "q.sql")
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        findings = judge(fused, load_catalog(), {"athena": "*"})
        assert "SF-ATH-002" in {f.rule_id for f in findings}

    def test_sf_ath_002_false_positive_guard_with_real_partition_filter(self):
        """LIMIT com filtro real sobre a coluna de particao NAO pode disparar."""
        sql_facts = extract_sql(
            "SELECT a, b FROM db.eventos WHERE dt = '2026-01-01' LIMIT 10", "q.sql"
        )
        catalog_facts = _catalog([PARQUET_EVENTOS])
        fused = fuse(sql_facts + catalog_facts)
        findings = judge(fused, load_catalog(), {"athena": "*"})
        assert "SF-ATH-002" not in {f.rule_id for f in findings}

    def test_sf_ath_002_skipped_without_any_catalog(self):
        sql_facts = extract_sql("SELECT a, b FROM db.eventos LIMIT 10", "q.sql")
        fused = fuse(sql_facts)
        findings, skipped = judge(fused, load_catalog(), {"athena": "*"}, return_skipped=True)
        assert "SF-ATH-002" not in {f.rule_id for f in findings}
        entry = next(s for s in skipped if s["rule_id"] == "SF-ATH-002")
        assert entry["reason"] == "requires_facts"
        assert "catalog.table_schema" in entry["missing"]

    def test_sf_ath_005_fires_on_partition_type_mismatch(self):
        table = {
            "name": "db.eventos",
            "storage_format": "parquet",
            "partition_keys": [{"name": "dt", "type": "bigint"}],
            "columns": [{"name": "dt", "type": "bigint"}],
        }
        sql_facts = extract_sql("SELECT a FROM db.eventos WHERE dt = '20260101'", "q.sql")
        catalog_facts = _catalog([table])
        fused = fuse(sql_facts + catalog_facts)
        findings = judge(fused, load_catalog(), {"athena": "*"})
        assert "SF-ATH-005" in {f.rule_id for f in findings}
