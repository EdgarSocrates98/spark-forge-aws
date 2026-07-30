import textwrap

from sparkforge.facts.pyspark_ast import EXTRACTOR_ID, extract_source


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


class TestPartitioning:
    def test_detects_coalesce_with_literal_one(self):
        src = textwrap.dedent(
            """
            def run(df):
                df.coalesce(1).write.parquet("s3://b/p")
            """
        )
        facts = extract_source(src, "lib/loader.py")
        got = facts_of("pyspark.partitioning", facts)
        assert len(got) == 1
        fact = got[0]
        assert fact.attrs["method"] == "coalesce"
        assert fact.attrs["literal_arg"] is True
        assert fact.measures["target_count"] == 1
        assert fact.subject["file"] == "lib/loader.py"
        assert fact.subject["line"] == 3
        assert fact.subject["symbol"] == "run"
        assert "coalesce" in fact.subject["snippet"]

    def test_detects_repartition_with_literal(self):
        src = "df.repartition(200)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["method"] == "repartition"
        assert facts[0].measures["target_count"] == 200
        assert facts[0].attrs["has_partition_expr"] is False

    def test_repartition_by_column_marks_partition_expr(self):
        src = 'df.repartition(200, "cliente_id")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["has_partition_expr"] is True

    def test_non_literal_arg_is_marked_and_has_no_measure(self):
        src = "df.repartition(n_particoes)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False
        assert "target_count" not in facts[0].measures

    def test_clean_code_yields_no_partitioning_facts(self):
        src = 'df.select("a").filter("a > 1").write.parquet("s3://b/p")\n'
        assert facts_of("pyspark.partitioning", extract_source(src, "a.py")) == []

    def test_negative_literal_is_recognized(self):
        src = "df.repartition(-5)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is True
        assert facts[0].measures["target_count"] == -5
        assert facts[0].attrs["has_partition_expr"] is False

    def test_positive_unary_literal_is_recognized(self):
        src = "df.repartition(+8)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is True
        assert facts[0].measures["target_count"] == 8
        assert facts[0].attrs["has_partition_expr"] is False

    def test_coalesce_true_stays_non_literal(self):
        src = "df.coalesce(True)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False
        assert "target_count" not in facts[0].measures

    def test_double_negation_stays_non_literal(self):
        src = "df.repartition(--5)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False

    def test_negative_literal_with_column_marks_partition_expr(self):
        src = 'df.repartition(-5, "col")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["has_partition_expr"] is True


class TestProvenanceAndDeterminism:
    def test_provenance_records_extractor_and_artifact(self):
        facts = extract_source("df.coalesce(1)\n", "lib/x.py")
        prov = facts[0].provenance
        assert prov["extractor"] == EXTRACTOR_ID
        assert prov["artifact"] == "lib/x.py"
        assert len(prov["artifact_sha256"]) == 64

    def test_same_input_twice_yields_identical_dicts(self):
        src = "df.coalesce(1)\ndf.repartition(10)\n"
        first = [f.to_dict() for f in extract_source(src, "a.py")]
        second = [f.to_dict() for f in extract_source(src, "a.py")]
        assert first == second


class TestUnresolved:
    def test_dynamic_dispatch_emits_unresolved_not_a_finding_candidate(self):
        src = "getattr(df, metodo)(1)\n"
        facts = extract_source(src, "a.py")
        assert facts_of("pyspark.unresolved", facts)
        assert facts_of("pyspark.partitioning", facts) == []

    def test_unresolved_records_reason_and_location(self):
        src = "getattr(df, metodo)(1)\n"
        fact = facts_of("pyspark.unresolved", extract_source(src, "a.py"))[0]
        assert fact.attrs["reason"] == "getattr"
        assert fact.subject["line"] == 1


class TestSyntaxError:
    def test_unparseable_file_yields_single_unresolved_fact(self):
        facts = extract_source("def broken(:\n", "bad.py")
        assert len(facts) == 1
        assert facts[0].kind == "pyspark.unresolved"
        assert facts[0].attrs["reason"] == "syntax_error"
