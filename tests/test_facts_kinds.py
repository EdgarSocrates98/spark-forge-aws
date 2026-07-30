import textwrap

from sparkforge.facts.pyspark_ast import extract_source

EXPECTED_KINDS = {
    "pyspark.read",
    "pyspark.write",
    "pyspark.action",
    "pyspark.driver_collect",
    "pyspark.udf",
    "pyspark.cache",
    "pyspark.partitioning",
    "pyspark.join",
    "pyspark.explode",
    "pyspark.window",
    "pyspark.chain",
    "pyspark.loop",
    "pyspark.withcolumn_run",
    "pyspark.conf_set",
    "pyspark.dedup",
    "pyspark.callgraph_edge",
    "pyspark.unresolved",
}


def kinds(src):
    return {f.kind for f in extract_source(src, "a.py")}


def one(kind, src):
    got = [f for f in extract_source(src, "a.py") if f.kind == kind]
    assert got, f"nenhum fact {kind}"
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    """Garante que as 17 kinds da spec secao 6.2 existem como constante."""
    from sparkforge.facts.pyspark_ast import EMITTED_KINDS

    assert EMITTED_KINDS == EXPECTED_KINDS


class TestReadWriteAction:
    def test_read_parquet(self):
        assert one("pyspark.read", 'spark.read.parquet("s3://b/p")\n').attrs["format"] == "parquet"

    def test_read_table(self):
        assert one("pyspark.read", 'spark.table("db.tbl")\n').attrs["target"] == "db.tbl"

    def test_spark_sql_is_a_read(self):
        assert one("pyspark.read", 'spark.sql("SELECT 1")\n').attrs["format"] == "sql"

    def test_write_records_mode(self):
        src = 'df.write.mode("append").parquet("s3://b/p")\n'
        assert one("pyspark.write", src).attrs["mode"] == "append"

    def test_writeto_append_is_a_write(self):
        assert one("pyspark.write", 'df.writeTo("db.tbl").append()\n').attrs["mode"] == "append"

    def test_count_is_an_action(self):
        assert one("pyspark.action", "df.count()\n").attrs["method"] == "count"


class TestUdf:
    def test_python_udf_decorator(self):
        src = textwrap.dedent(
            """
            @udf(returnType=StringType())
            def normaliza(x):
                return x.strip()
            """
        )
        assert one("pyspark.udf", src).attrs["udf_type"] == "python"

    def test_pandas_udf_decorator_is_distinguished(self):
        src = textwrap.dedent(
            """
            @pandas_udf("string")
            def normaliza(s):
                return s
            """
        )
        assert one("pyspark.udf", src).attrs["udf_type"] == "pandas"

    def test_udf_call_form(self):
        src = "f = udf(minha_funcao, StringType())\n"
        assert one("pyspark.udf", src).attrs["udf_type"] == "python"


class TestCache:
    def test_cache_without_unpersist_in_scope(self):
        src = textwrap.dedent(
            """
            def run(df):
                d = df.cache()
                return d.count()
            """
        )
        assert one("pyspark.cache", src).attrs["has_unpersist_in_scope"] is False

    def test_cache_with_unpersist_in_same_function(self):
        src = textwrap.dedent(
            """
            def run(df):
                d = df.cache()
                n = d.count()
                d.unpersist()
                return n
            """
        )
        assert one("pyspark.cache", src).attrs["has_unpersist_in_scope"] is True


class TestJoinExplodeWindowDedup:
    def test_join_records_how_and_broadcast_hint(self):
        src = 'a.join(broadcast(b), "k", how="left")\n'
        fact = one("pyspark.join", src)
        assert fact.attrs["how"] == "left"
        assert fact.attrs["has_broadcast_hint"] is True

    def test_join_without_hint(self):
        assert one("pyspark.join", 'a.join(b, "k")\n').attrs["has_broadcast_hint"] is False

    def test_explode_variant(self):
        src = 'df.select(explode(col("arr")))\n'
        assert one("pyspark.explode", src).attrs["variant"] == "explode"

    def test_window_partition_by(self):
        src = 'w = Window.partitionBy("k").orderBy("ts")\n'
        fact = one("pyspark.window", src)
        assert fact.attrs["has_partition_by"] is True
        assert fact.attrs["has_order_by"] is True

    def test_dedup_without_explicit_columns(self):
        src = "df.dropDuplicates()\n"
        assert one("pyspark.dedup", src).attrs["has_explicit_columns"] is False

    def test_dedup_with_explicit_columns(self):
        src = 'df.dropDuplicates(["k"])\n'
        assert one("pyspark.dedup", src).attrs["has_explicit_columns"] is True


class TestLoopAndConf:
    def test_loop_containing_write_is_flagged(self):
        src = textwrap.dedent(
            """
            for lote in lotes:
                df.filter(col("lote") == lote).write.parquet("s3://b/p")
            """
        )
        fact = one("pyspark.loop", src)
        assert fact.attrs["contains_write"] is True
        assert fact.measures["loop_depth"] == 1

    def test_loop_containing_action_is_flagged(self):
        src = "for x in xs:\n    print(df.count())\n"
        assert one("pyspark.loop", src).attrs["contains_action"] is True

    def test_loop_without_spark_work_is_not_emitted(self):
        assert "pyspark.loop" not in kinds("for x in xs:\n    total += x\n")

    def test_conf_set_records_key_and_value(self):
        src = 'spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
        fact = one("pyspark.conf_set", src)
        assert fact.attrs["key"] == "spark.sql.shuffle.partitions"
        assert fact.attrs["value"] == "800"


class TestCallgraph:
    def test_function_to_function_edge(self):
        src = textwrap.dedent(
            """
            def helper(df):
                return df

            def run(df):
                return helper(df)
            """
        )
        edge = one("pyspark.callgraph_edge", src)
        assert edge.attrs["caller"] == "run"
        assert edge.attrs["callee"] == "helper"


class TestCleanFixtureStaysClean:
    def test_idiomatic_code_emits_no_anti_pattern_kinds(self):
        src = textwrap.dedent(
            """
            def run(spark):
                d = spark.read.parquet("s3://b/p")
                return (
                    d.select("a", "b")
                    .filter("a > 1")
                    .write.mode("append")
                    .parquet("s3://b/out")
                )
            """
        )
        got = kinds(src)
        assert "pyspark.unresolved" not in got
        assert "pyspark.driver_collect" not in got
        assert "pyspark.udf" not in got
        assert "pyspark.partitioning" not in got
