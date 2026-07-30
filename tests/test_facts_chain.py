from sparkforge.facts.pyspark_ast import extract_source


def only(kind, facts):
    got = [f for f in facts if f.kind == kind]
    assert len(got) == 1, f"esperado 1 fact {kind}, veio {len(got)}"
    return got[0]


class TestChainOrder:
    def test_records_ordered_methods(self):
        src = 'df.select("a").join(o, "k").filter("a > 1").write.parquet("s3://b/p")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.attrs["methods"] == ["select", "join", "filter", "write", "parquet"]

    def test_join_index_and_first_reduction_index_when_join_is_late(self):
        src = 'df.select("a").filter("a > 1").join(o, "k")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.measures["join_index"] == 2
        assert chain.measures["first_reduction_index"] == 0

    def test_join_before_reduction_is_visible_in_measures(self):
        src = 'df.join(o, "k").select("a").filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.measures["join_index"] == 0
        assert chain.measures["first_reduction_index"] == 1

    def test_chain_without_join_has_no_join_index(self):
        src = 'df.select("a").filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert "join_index" not in chain.measures

    def test_chain_span_covers_multiline(self):
        src = 'df.select("a") \\\n  .join(o, "k") \\\n  .filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.subject["line"] == 1
        assert chain.subject["end_line"] >= 3

    def test_single_call_is_not_a_chain(self):
        facts = extract_source("df.count()\n", "a.py")
        assert [f for f in facts if f.kind == "pyspark.chain"] == []


class TestBoundedDetection:
    def test_collect_after_limit_is_bounded(self):
        src = "rows = df.limit(10).collect()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is True

    def test_collect_without_limit_is_unbounded(self):
        src = "rows = df.collect()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is False

    def test_topandas_without_limit_is_unbounded(self):
        src = "pdf = df.toPandas()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is False


class TestWithColumnRun:
    def test_counts_consecutive_withcolumn(self):
        calls = "".join(f'.withColumn("c{i}", lit(1))' for i in range(12))
        fact = only("pyspark.withcolumn_run", extract_source("df" + calls + "\n", "a.py"))
        assert fact.measures["run_length"] == 12

    def test_below_threshold_still_emits_the_fact(self):
        """Extrator nao aplica limiar. Emite a contagem; a regra decide."""
        calls = "".join(f'.withColumn("c{i}", lit(1))' for i in range(9))
        fact = only("pyspark.withcolumn_run", extract_source("df" + calls + "\n", "a.py"))
        assert fact.measures["run_length"] == 9
