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
    "pyspark.function_def",
    "pyspark.unresolved",
    "pyspark.module_analyzed",
    "pyspark.glue_context_init",
}


def kinds(src):
    return {f.kind for f in extract_source(src, "a.py")}


def one(kind, src):
    got = [f for f in extract_source(src, "a.py") if f.kind == kind]
    assert got, f"nenhum fact {kind}"
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    """Garante que as 20 kinds (17 da spec secao 6.2 + sentinelas + `function_def`).

    `pyspark.function_def` entrou na Fase 5b: sem um fact por funcao DEFINIDA,
    o grafo de chamadas so conhecia funcoes que aparecem em alguma aresta, e
    uma funcao definida e nunca chamada era invisivel.
    """
    from sparkforge.facts.pyspark_ast import EMITTED_KINDS

    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 20
    assert "pyspark.module_analyzed" in EMITTED_KINDS
    assert "pyspark.glue_context_init" in EMITTED_KINDS


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


class TestFunctionDef:
    """Um fact por funcao DEFINIDA -- a base do no de grafo sem aresta.

    Cada atributo aqui existe para decidir uma coisa so: se a ausencia de
    chamador significa algo. Metodo, funcao aninhada e funcao decorada sao
    chamados por caminhos que o AST intra-arquivo nao ve; sem `def_kind` e
    `decorators`, "ninguem chama" seria lido como "e codigo morto" nos tres.
    """

    @staticmethod
    def defs(src):
        return {
            f.subject["symbol"]: f
            for f in extract_source(textwrap.dedent(src), "a.py")
            if f.kind == "pyspark.function_def"
        }

    def test_module_level_function_is_emitted_even_without_any_call(self):
        found = self.defs("def orfa():\n    return 1\n")
        assert set(found) == {"orfa"}
        assert found["orfa"].attrs["def_kind"] == "module"
        assert found["orfa"].measures["name_reference_count"] == 0

    def test_symbol_is_the_function_itself_not_the_enclosing_scope(self):
        """O no do grafo e chaveado por (arquivo, simbolo): se o subject
        trouxesse o escopo de fora, a definicao aninhada seria contada como se
        fosse a de fora."""
        found = self.defs("def externa():\n    def interna():\n        return 1\n")
        assert set(found) == {"externa", "interna"}
        assert found["interna"].attrs["def_kind"] == "nested"
        assert found["interna"].attrs["enclosing"] == "externa"

    def test_method_is_marked_with_its_class(self):
        found = self.defs("class Pipeline:\n    def run(self):\n        return 1\n")
        assert found["run"].attrs["def_kind"] == "method"
        assert found["run"].attrs["enclosing"] == "Pipeline"

    def test_decorators_are_recorded_with_dotted_name(self):
        src = """
            import functools

            @functools.lru_cache
            def cara():
                return 1
        """
        assert self.defs(src)["cara"].attrs["decorators"] == ["functools.lru_cache"]

    def test_all_declares_the_function_as_exported(self):
        src = """
            __all__ = ["publica"]

            def publica():
                return 1

            def privada():
                return 2
        """
        found = self.defs(src)
        assert found["publica"].attrs["exported"] is True
        assert found["privada"].attrs["exported"] is False

    def test_reference_by_name_is_counted_even_without_a_call(self):
        """Callback e tabela de despacho nao produzem aresta nenhuma. Sem esta
        contagem, `trata` pareceria uma funcao que ninguem usa."""
        src = """
            def main():
                rdd.foreach(trata)

            def trata(row):
                return row
        """
        assert self.defs(src)["trata"].measures["name_reference_count"] == 1

    def test_module_level_call_counts_as_a_reference(self):
        src = """
            def main():
                return 1

            if __name__ == "__main__":
                main()
        """
        assert self.defs(src)["main"].measures["name_reference_count"] == 1

    def test_self_recursion_does_not_count_as_an_external_reference(self):
        src = """
            def sozinha(n):
                return sozinha(n - 1)
        """
        assert self.defs(src)["sozinha"].measures["name_reference_count"] == 0

    def test_async_function_is_emitted_and_marked(self):
        found = self.defs("async def busca():\n    return 1\n")
        assert found["busca"].attrs["is_async"] is True


class TestModuleAnalyzedSentinel:
    def test_emitted_once_for_parseable_file(self):
        facts = [
            f
            for f in extract_source("df.coalesce(1)\n", "a.py")
            if f.kind == "pyspark.module_analyzed"
        ]
        assert len(facts) == 1
        assert facts[0].attrs["parsed"] is True

    def test_not_emitted_for_syntax_error_file(self):
        facts = extract_source("def broken(:\n", "bad.py")
        assert {f.kind for f in facts} == {"pyspark.unresolved"}

    def test_not_emitted_for_too_deep_file(self):
        facts = extract_source("-" * 10000 + "1\n", "deep.py")
        assert {f.kind for f in facts} == {"pyspark.unresolved"}

    def test_unresolved_count_reflects_real_count(self):
        src = "getattr(df, m1)(1)\ngetattr(df, m2)(2)\n"
        fact = one("pyspark.module_analyzed", src)
        assert fact.measures["unresolved_count"] == 2

    def test_referenced_names_covers_both_import_forms(self):
        """As duas formas de usar uma funcao de OUTRO modulo: `from lib import
        limpa` chama `limpa(df)` (um Name), `import lib` chama `lib.limpa(df)`
        (um Attribute). Quem consome cruza esta lista para nao acusar de orfa
        uma funcao que so e usada entre arquivos."""
        src = "from lib import limpa\nimport outra\n\nlimpa(df)\noutra.trata(df)\n"
        names = one("pyspark.module_analyzed", src).attrs["referenced_names"]
        assert "limpa" in names
        assert "trata" in names
        assert names == sorted(set(names))


class TestGlueContextInit:
    def test_bare_call_form(self):
        src = "glueContext = GlueContext(sc)\n"
        assert one("pyspark.glue_context_init", src).attrs["form"] == "call"

    def test_attribute_call_form(self):
        src = "glueContext = awsglue.context.GlueContext(sc)\n"
        assert one("pyspark.glue_context_init", src).attrs["form"] == "call"

    def test_not_emitted_for_pure_sparksession_job(self):
        src = textwrap.dedent(
            """
            from pyspark.sql import SparkSession

            spark = SparkSession.builder.appName("job").getOrCreate()
            """
        )
        assert "pyspark.glue_context_init" not in kinds(src)


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


class TestNoDuplicateReadFacts:
    """`spark.read.format(x).load(y)` e uma operacao de leitura, nao duas.

    O AST da a chamadas encadeadas o mesmo lineno/col_offset, entao dois facts
    para a mesma expressao recebiam `subject` identico e portanto o mesmo
    `Fact.id` — dois facts com conteudo diferente colidindo num id. Isso quebra a
    rastreabilidade que o id existe para garantir.
    """

    def _reads(self, src):
        return [f for f in extract_source(src, "a.py") if f.kind == "pyspark.read"]

    def test_format_then_load_is_one_read(self):
        reads = self._reads('spark.read.format("parquet").load(p)\n')
        assert len(reads) == 1
        assert reads[0].attrs["format"] == "load"

    def test_three_hop_builder_chain_is_one_read(self):
        """`.format().option().load()` tem um elo nao-terminal no meio: uma
        checagem de um unico hop deixaria `format` e `load` emitirem dois facts."""
        reads = self._reads('spark.read.format("iceberg").option("k", "v").load(t)\n')
        assert len(reads) == 1
        assert reads[0].attrs["format"] == "load"

    def test_plain_parquet_read_is_one_read(self):
        assert len(self._reads('spark.read.parquet("p")\n')) == 1

    def test_read_followed_by_transformation_is_still_one_read(self):
        assert len(self._reads('spark.read.format("parquet").load(p).select("a")\n')) == 1

    def test_no_two_facts_share_an_id(self):
        src = 'spark.read.format("parquet").load(p).select("a").filter("a > 1")\n'
        facts = extract_source(src, "a.py")
        ids = [f.id for f in facts]
        assert len(ids) == len(set(ids)), "facts com id colidente"
