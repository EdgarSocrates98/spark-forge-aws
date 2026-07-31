from sparkforge.facts.sql_literal import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    extract_sql,
    extract_sql_from_pyspark,
)
from sparkforge.findings.validate import validate_fact

EXPECTED_KINDS = {"sql.projection", "sql.predicate", "sql.unresolved", "sql.analyzed"}


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def one(kind, sql, path="q.sql"):
    got = facts_of(kind, extract_sql(sql, path))
    assert got, f"nenhum fact {kind}"
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 4
    assert EXTRACTOR_ID.startswith("sql_literal@")


class TestProjection:
    def test_select_star(self):
        fact = one("sql.projection", "SELECT * FROM t")
        assert fact.attrs["star"] is True
        assert fact.attrs["has_limit"] is False
        assert fact.attrs["table_format_columnar"] is None
        assert "column_count" not in fact.measures

    def test_qualified_star(self):
        fact = one("sql.projection", "SELECT t.* FROM t")
        assert fact.attrs["star"] is True

    def test_explicit_columns_have_column_count(self):
        fact = one("sql.projection", "SELECT a, b, c FROM t")
        assert fact.attrs["star"] is False
        assert fact.measures["column_count"] == 3

    def test_function_call_commas_do_not_split_columns(self):
        fact = one("sql.projection", "SELECT SUM(a, b), c FROM t")
        assert fact.measures["column_count"] == 2

    def test_has_limit_true(self):
        fact = one("sql.projection", "SELECT a FROM t LIMIT 10")
        assert fact.attrs["has_limit"] is True

    def test_has_limit_false(self):
        fact = one("sql.projection", "SELECT a FROM t")
        assert fact.attrs["has_limit"] is False

    def test_missing_select_from_is_unresolved(self):
        facts = extract_sql("not sql at all", "q.sql")
        unresolved = facts_of("sql.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "unparsed_clause"
        assert not facts_of("sql.projection", facts)


class TestPredicate:
    def test_simple_equality(self):
        fact = one("sql.predicate", "SELECT a FROM t WHERE dt = '2026-01-01'")
        assert fact.attrs["column"] == "dt"
        assert fact.attrs["operator"] == "="
        assert fact.attrs["value"] == "'2026-01-01'"
        assert fact.attrs["on_partition_column"] is None
        assert fact.attrs["type_mismatch"] is None

    def test_multiple_and_predicates(self):
        facts = facts_of(
            "sql.predicate", extract_sql("SELECT a FROM t WHERE x > 1 AND y = 2", "q.sql")
        )
        assert len(facts) == 2
        assert {f.attrs["column"] for f in facts} == {"x", "y"}

    def test_qualified_column_quotes_stripped(self):
        fact = one("sql.predicate", 'SELECT a FROM t WHERE "dt" = 1')
        assert fact.attrs["column"] == "dt"

    def test_or_predicate_is_unresolved_not_guessed(self):
        facts = extract_sql("SELECT a FROM t WHERE x = 1 OR y = 2", "q.sql")
        assert facts_of("sql.predicate", facts) == []
        unresolved = facts_of("sql.unresolved", facts)
        assert unresolved
        assert unresolved[0].attrs["reason"] == "unparsed_clause"

    def test_no_where_clause_produces_no_predicate_facts(self):
        facts = extract_sql("SELECT a FROM t", "q.sql")
        assert facts_of("sql.predicate", facts) == []

    def test_where_stops_at_group_by(self):
        facts = facts_of(
            "sql.predicate",
            extract_sql("SELECT a FROM t WHERE x = 1 GROUP BY a", "q.sql"),
        )
        assert len(facts) == 1
        assert facts[0].attrs["column"] == "x"


class TestSentinel:
    def test_counts_reflect_projection_and_predicates(self):
        fact = one("sql.analyzed", "SELECT a, b FROM t WHERE x = 1 AND y = 2")
        assert fact.measures["projection_count"] == 1
        assert fact.measures["predicate_count"] == 2
        assert fact.measures["unresolved_count"] == 0
        assert fact.measures["statement_count"] == 1


class TestExtractSqlFromPyspark:
    def test_literal_spark_sql_is_extracted(self):
        source = 'df = spark.sql("SELECT a FROM t WHERE x = 1")\n'
        facts = extract_sql_from_pyspark(source, "job.py")
        proj = facts_of("sql.projection", facts)
        pred = facts_of("sql.predicate", facts)
        assert proj and pred
        assert proj[0].subject["line"] == 1

    def test_fstring_argument_is_non_literal_sql(self):
        source = 'df = spark.sql(f"SELECT * FROM {tbl}")\n'
        facts = extract_sql_from_pyspark(source, "job.py")
        unresolved = facts_of("sql.unresolved", facts)
        assert any(f.attrs["reason"] == "non_literal_sql" for f in unresolved)
        assert not facts_of("sql.projection", facts)

    def test_variable_argument_is_non_literal_sql(self):
        source = "q = build_query()\ndf = spark.sql(q)\n"
        facts = extract_sql_from_pyspark(source, "job.py")
        unresolved = facts_of("sql.unresolved", facts)
        assert any(f.attrs["reason"] == "non_literal_sql" for f in unresolved)

    def test_non_spark_sql_method_is_ignored(self):
        source = 'x = something.sql("SELECT a FROM t")\n'
        facts = extract_sql_from_pyspark(source, "job.py")
        assert not facts_of("sql.projection", facts)
        assert not facts_of("sql.unresolved", facts)

    def test_one_sentinel_per_file_aggregating_all_calls(self):
        source = (
            'a = spark.sql("SELECT x FROM t1")\n'
            'b = spark.sql("SELECT y FROM t2 WHERE z = 1")\n'
        )
        facts = extract_sql_from_pyspark(source, "job.py")
        sentinels = facts_of("sql.analyzed", facts)
        assert len(sentinels) == 1
        assert sentinels[0].measures["statement_count"] == 2
        assert sentinels[0].measures["projection_count"] == 2
        assert sentinels[0].measures["predicate_count"] == 1

    def test_syntax_error_in_host_file_is_read_error(self):
        facts = extract_sql_from_pyspark("def f(:\n", "job.py")
        assert len(facts) == 1
        assert facts[0].kind == "sql.unresolved"
        assert facts[0].attrs["reason"] == "read_error"

    def test_no_spark_sql_calls_produces_only_a_zero_sentinel(self):
        facts = extract_sql_from_pyspark("x = 1\n", "job.py")
        assert len(facts) == 1
        assert facts[0].kind == "sql.analyzed"
        assert facts[0].measures["statement_count"] == 0


class TestSchemaValidity:
    def test_every_fact_validates(self):
        source = 'a = spark.sql("SELECT * FROM t WHERE x = 1 LIMIT 5")\n'
        for fact in extract_sql_from_pyspark(source, "job.py"):
            validate_fact(fact.to_dict())

    def test_kind_namespace_never_leaks_unknown_kind(self):
        facts = extract_sql("SELECT a, b FROM t WHERE x = 1 OR y = 2", "q.sql")
        assert {f.kind for f in facts} <= EMITTED_KINDS
