import random
import textwrap

from sparkforge.facts.call_graph import EMITTED_KINDS, build_call_graph
from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.models import Fact
from sparkforge.findings.validate import validate_fact

FILE = "lib.py"


def edge(caller: str, callee: str, file: str = FILE, line: int = 1) -> Fact:
    return Fact(
        kind="pyspark.callgraph_edge",
        subject={
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "end_line": line,
            "symbol": caller,
            "snippet": f"{callee}()",
        },
        attrs={"caller": caller, "callee": callee},
        provenance={"artifact": file, "artifact_sha256": "", "extractor": "pyspark_ast@0.1.0"},
    )


def work(symbol: str, kind: str = "pyspark.action", file: str = FILE, line: int = 1) -> Fact:
    return Fact(
        kind=kind,
        subject={
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "end_line": line,
            "symbol": symbol,
            "snippet": "df.count()",
        },
        attrs={"method": "count"},
        provenance={"artifact": file, "artifact_sha256": "", "extractor": "pyspark_ast@0.1.0"},
    )


def by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_emitted_kinds_are_exactly_four():
    assert EMITTED_KINDS == {
        "callgraph.function",
        "callgraph.reachable_spark_work",
        "callgraph.summary",
        "callgraph.cycle",
    }


class TestLinearChainDepth:
    def test_collect_two_levels_deep_reports_min_depth_two(self):
        facts = [edge("main", "a"), edge("a", "b"), work("b", "pyspark.driver_collect")]
        out = build_call_graph(facts, path_hint=FILE)

        reachable = by_kind(out, "callgraph.reachable_spark_work")
        collect_fact = next(
            f for f in reachable if f.attrs["work_kind"] == "pyspark.driver_collect"
        )
        assert collect_fact.measures["min_depth"] == 2
        assert collect_fact.attrs["via"] == ["main", "a", "b"]
        assert collect_fact.attrs["entrypoint"] == "main"

    def test_entrypoint_has_no_callers(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        functions = {f.subject["symbol"]: f for f in by_kind(out, "callgraph.function")}
        assert functions["main"].measures["fan_in"] == 0
        assert functions["main"].attrs["is_entrypoint"] is True
        assert functions["a"].attrs["is_entrypoint"] is False

    def test_terminal_function_is_a_leaf(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        functions = {f.subject["symbol"]: f for f in by_kind(out, "callgraph.function")}
        assert functions["b"].measures["fan_out"] == 0
        assert functions["b"].attrs["is_leaf"] is True
        assert functions["main"].attrs["is_leaf"] is False

    def test_summary_reports_max_depth_and_no_unreachable(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["max_depth"] == 2
        assert summary.measures["function_count"] == 3
        assert summary.measures["edge_count"] == 2
        assert summary.measures["unreachable_from_entrypoint_count"] == 0
        assert summary.attrs["entrypoints"] == ["main"]
        assert summary.attrs["has_cycle"] is False


class TestCycles:
    def test_direct_recursion_produces_self_cycle(self):
        facts = [edge("f", "f")]
        out = build_call_graph(facts, path_hint=FILE)
        cycles = by_kind(out, "callgraph.cycle")
        assert len(cycles) == 1
        assert cycles[0].attrs["functions"] == ["f"]
        assert cycles[0].measures["length"] == 1

        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.attrs["has_cycle"] is True

    def test_mutual_recursion_produces_one_canonical_cycle_regardless_of_edge_order(self):
        forward = [edge("f", "g"), edge("g", "f")]
        backward = [edge("g", "f"), edge("f", "g")]

        out_forward = build_call_graph(forward, path_hint=FILE)
        out_backward = build_call_graph(backward, path_hint=FILE)

        assert [f.to_dict() for f in out_forward] == [f.to_dict() for f in out_backward]

        cycles = by_kind(out_forward, "callgraph.cycle")
        assert len(cycles) == 1
        assert cycles[0].attrs["functions"] == ["f", "g"]

    def test_cycle_containing_spark_work_is_flagged(self):
        facts = [edge("f", "g"), edge("g", "f"), work("g", "pyspark.write")]
        out = build_call_graph(facts, path_hint=FILE)
        cycle = by_kind(out, "callgraph.cycle")[0]
        assert cycle.attrs["contains_spark_work"] is True
        assert cycle.measures["spark_work_count"] == 1

    def test_cycle_with_no_entrypoint_counts_as_unreachable(self):
        # f <-> g calling each other, nothing outside calls either: no
        # entrypoint exists, so no BFS ever visits them. Este e o UNICO caso
        # que a medida antiga pegava -- e o motivo de ela ter sido renomeada
        # para `unreachable_from_entrypoint_count`.
        facts = [edge("f", "g"), edge("g", "f")]
        out = build_call_graph(facts, path_hint=FILE)
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["entrypoint_count"] == 0
        assert summary.measures["unreachable_from_entrypoint_count"] == 2
        assert by_kind(out, "callgraph.reachable_spark_work") == []


class TestIsolatedFunction:
    def test_work_fact_without_definition_or_edge_produces_no_node(self):
        """Degradacao explicita: sem `pyspark.function_def` na entrada, o grafo
        volta ao comportamento anterior a Fase 5b -- so nos de aresta. E o que
        acontece com facts gravados por um extrator antigo, e
        `defined_function_count` e o que denuncia a diferenca."""
        facts = [work("solo", "pyspark.action")]
        out = build_call_graph(facts, path_hint=FILE)
        assert by_kind(out, "callgraph.function") == []
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["function_count"] == 0
        assert summary.measures["defined_function_count"] == 0
        assert summary.measures["edge_count"] == 0
        assert summary.measures["unreferenced_function_count"] == 0


def graph_of(source: str, path: str = FILE):
    return build_call_graph(extract_source(textwrap.dedent(source), path), path_hint=path)


def summary_of(source: str):
    return by_kind(graph_of(source), "callgraph.summary")[0]


def functions_of(source: str):
    return {f.subject["symbol"]: f for f in by_kind(graph_of(source), "callgraph.function")}


class TestDefinedFunctionBecomesANode:
    """A divida da Fase 1: uma funcao DEFINIDA e nunca chamada nao existia.

    Antes, `nodes` vinha so das arestas, entao a funcao morta tipica -- a que
    nao chama ninguem e ninguem chama -- nao entrava no grafo, e
    `unreachable_function_count` devolvia ZERO. Zero indistinguivel de "nao ha
    codigo morto" e o falso negativo silencioso que este repositorio trata como
    o pior defeito.
    """

    def test_function_never_called_that_calls_nobody_is_a_node(self):
        src = """
            def main():
                spark.read.parquet("s3://in").count()

            def orfa():
                return 1
        """
        summary = summary_of(src)
        assert summary.measures["function_count"] == 2
        assert summary.measures["defined_function_count"] == 2
        assert "orfa" in summary.attrs["unreferenced_functions"]

    def test_function_never_called_that_calls_another_is_still_flagged(self):
        src = """
            def orfa():
                return ajudante()

            def ajudante():
                return 2
        """
        summary = summary_of(src)
        assert summary.attrs["unreferenced_functions"] == ["orfa"]

    def test_the_entrypoint_itself_becomes_a_node_and_carries_its_spark_work(self):
        """Antes, um script cujo unico `main` faz `collect()` produzia ZERO
        fact de grafo: `main` nao aparecia em aresta nenhuma."""
        src = """
            def main():
                spark.read.parquet("s3://in").collect()
        """
        out = graph_of(src)
        assert [f.subject["symbol"] for f in by_kind(out, "callgraph.function")] == ["main"]
        reachable = by_kind(out, "callgraph.reachable_spark_work")
        assert {f.attrs["work_kind"] for f in reachable} >= {"pyspark.driver_collect"}


class TestWhatAbsenceOfCallerCanMean:
    """Onde "ninguem chama" NAO e informacao sobre o codigo.

    Cada caso aqui e uma forma de invocacao que o extrator intra-arquivo nao
    ve. Contar qualquer um deles como orfao seria falso positivo em massa --
    o defeito que `rules/catalog/README.md` considera pior que achado nenhum,
    porque destroi a confianca no relatorio inteiro.
    """

    def test_method_is_opaque_because_the_call_is_an_attribute(self):
        src = """
            class Pipeline:
                def nunca_chamado(self):
                    return 1
        """
        fact = functions_of(src)["nunca_chamado"]
        assert fact.attrs["def_kind"] == "method"
        assert fact.attrs["caller_visibility"] == "opaque"
        assert fact.attrs["is_unreferenced"] is False

    def test_nested_function_stays_measurable_because_any_use_reads_its_name(self):
        """Funcao aninhada NAO e opaca: devolve-la (`return interna`), chama-la
        ou passa-la adiante sao todas leituras do nome, e leitura de nome e
        contada. Excluir aninhada seria abrir um buraco onde codigo morto
        cabe."""
        usada = """
            def externa():
                def interna():
                    return 1
                return interna
        """
        fact = functions_of(usada)["interna"]
        assert fact.attrs["def_kind"] == "nested"
        assert fact.attrs["caller_visibility"] == "resolvable"
        assert fact.attrs["is_unreferenced"] is False

        nunca_usada = """
            def externa():
                def interna():
                    return 1
                return 2
        """
        assert functions_of(nunca_usada)["interna"].attrs["is_unreferenced"] is True

    def test_decorated_function_is_opaque_because_a_framework_may_invoke_it(self):
        src = """
            import functools

            @functools.lru_cache
            def registrada():
                return 1
        """
        assert functions_of(src)["registrada"].attrs["caller_visibility"] == "opaque"

    def test_function_exported_in_all_is_opaque_because_the_caller_is_outside(self):
        """O caso CENTRAL: este repositorio existe para analisar bibliotecas
        Glue, onde a funcao publica nunca tem chamador dentro do corpus."""
        src = """
            __all__ = ["limpa"]

            def limpa(df):
                return df.dropDuplicates()
        """
        fact = functions_of(src)["limpa"]
        assert fact.attrs["caller_visibility"] == "opaque"
        assert fact.attrs["is_unreferenced"] is False

    def test_callback_passed_by_name_is_referenced_without_any_edge(self):
        src = """
            def main():
                rdd.foreach(trata)

            def trata(row):
                return row
        """
        fact = functions_of(src)["trata"]
        assert fact.measures["fan_in"] == 0
        assert fact.measures["name_reference_count"] == 1
        assert fact.attrs["is_unreferenced"] is False

    def test_dispatch_table_entry_is_referenced_without_any_edge(self):
        src = """
            def main():
                return {"limpa": limpa}

            def limpa(df):
                return df
        """
        assert functions_of(src)["limpa"].attrs["is_unreferenced"] is False

    def test_module_level_call_keeps_main_out_of_the_list(self):
        src = """
            def main():
                spark.read.parquet("s3://in").count()

            if __name__ == "__main__":
                main()
        """
        assert summary_of(src).attrs["unreferenced_functions"] == []

    def test_getattr_in_the_corpus_is_declared_on_the_summary(self):
        """Despacho por string nao e observavel. A medida nao pode fingir que
        e: quem le a lista precisa saber que existe `getattr` no corpus."""
        src = """
            def main():
                getattr(mod, nome)()

            def talvez_chamada():
                return 1
        """
        summary = summary_of(src)
        assert summary.attrs["dynamic_dispatch_present"] is True
        assert "talvez_chamada" in summary.attrs["unreferenced_functions"]


class TestCrossModuleReference:
    def test_function_used_only_by_another_file_is_not_reported_as_orphan(self):
        """Sem isto, a biblioteca inteira apareceria como orfa: as arestas de
        `pyspark_ast` sao intra-arquivo por construcao."""
        lib = "def limpa(df):\n    return df.dropDuplicates()\n\ndef morta(df):\n    return df\n"
        job = "from lib import limpa\n\ndef main():\n    limpa(df)\n"
        facts = extract_source(lib, "lib.py") + extract_source(job, "job.py")
        out = build_call_graph(facts, path_hint="corpus")
        functions = {(f.subject["file"], f.subject["symbol"]): f for f in
                     by_kind(out, "callgraph.function")}
        assert functions[("lib.py", "limpa")].attrs["referenced_in_other_module"] is True
        assert functions[("lib.py", "limpa")].attrs["is_unreferenced"] is False
        assert functions[("lib.py", "morta")].attrs["is_unreferenced"] is True

    def test_attribute_call_form_also_counts(self):
        lib = "def limpa(df):\n    return df\n"
        job = "import lib\n\ndef main():\n    lib.limpa(df)\n"
        facts = extract_source(lib, "lib.py") + extract_source(job, "job.py")
        summary = by_kind(build_call_graph(facts, path_hint="corpus"), "callgraph.summary")[0]
        assert "limpa" not in summary.attrs["unreferenced_functions"]


class TestHomonymDefinitions:
    def test_two_definitions_with_the_same_name_are_counted_not_hidden(self):
        """Dois `def` homonimos no mesmo arquivo colapsam num no -- a chave e
        (arquivo, nome). `definition_count` deixa a colisao visivel em vez de
        fazer o grafo mentir sobre quantas funcoes existem."""
        src = """
            class A:
                def run(self):
                    return 1

            class B:
                def run(self):
                    return 2
        """
        fact = functions_of(src)["run"]
        assert fact.measures["definition_count"] == 2


class TestDefinitionFactsAreNotSparkWork:
    def test_a_cycle_of_plain_functions_is_not_marked_as_containing_spark_work(self):
        """`pyspark.function_def` existe uma vez por funcao. Se ele contasse
        como trabalho Spark, TODA recursao dispararia SF-CG-001 (P1)."""
        src = """
            def f(n):
                return g(n)

            def g(n):
                return f(n)
        """
        cycle = by_kind(graph_of(src), "callgraph.cycle")[0]
        assert cycle.measures["spark_work_count"] == 0
        assert cycle.attrs["contains_spark_work"] is False


class TestDeterminism:
    def test_output_is_identical_across_shuffled_input_order(self):
        source = textwrap.dedent(
            """
            def main():
                stage_one()
                stage_two()

            def stage_one():
                helper()

            def stage_two():
                df.write.parquet("s3://out")

            def helper():
                df.collect()
            """
        )
        facts = extract_source(source, FILE)
        ordered = build_call_graph(facts, path_hint=FILE)

        shuffled = list(facts)
        random.Random(42).shuffle(shuffled)  # noqa: S311 -- deterministico p/ teste, nao cripto
        reshuffled = build_call_graph(shuffled, path_hint=FILE)

        assert [f.to_dict() for f in ordered] == [f.to_dict() for f in reshuffled]

    def test_writing_twice_produces_byte_identical_fact_ids(self):
        facts = [edge("main", "a"), work("a", "pyspark.driver_collect")]
        first = [f.id for f in build_call_graph(facts, path_hint=FILE)]
        second = [f.id for f in build_call_graph(list(reversed(facts)), path_hint=FILE)]
        assert first == second


class TestDeepChainDoesNotRecurse:
    def test_five_hundred_deep_chain_does_not_raise_recursion_error(self):
        depth = 500
        facts = [edge(f"f{i}", f"f{i + 1}") for i in range(depth)]
        facts.append(work(f"f{depth}", "pyspark.driver_collect"))

        out = build_call_graph(facts, path_hint=FILE)

        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["max_depth"] == depth
        assert summary.measures["function_count"] == depth + 1

        reachable = by_kind(out, "callgraph.reachable_spark_work")
        deep_work = next(f for f in reachable if f.attrs["work_kind"] == "pyspark.driver_collect")
        assert deep_work.measures["min_depth"] == depth


class TestSchemaValidity:
    def test_every_emitted_fact_validates_against_fact_schema(self):
        facts = [
            edge("main", "a"),
            edge("a", "b"),
            edge("f", "f"),
            edge("g", "h"),
            edge("h", "g"),
            work("b", "pyspark.driver_collect"),
            work("g", "pyspark.write"),
        ]
        out = build_call_graph(facts, path_hint=FILE)
        assert out  # sanity: something was produced
        for fact in out:
            validate_fact(fact.to_dict())


class TestFixtureIntegration:
    def test_action_in_loop_fixture_produces_a_valid_call_graph(self):
        from pathlib import Path

        fixture = (
            Path(__file__).resolve().parents[1] / "fixtures" / "pyspark" / "action_in_loop"
        )
        source_path = fixture / "input" / "lib" / "job.py"
        facts = extract_source(source_path.read_text(encoding="utf-8"), "input/lib/job.py")
        out = build_call_graph(facts, path_hint="input/lib/job.py")
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["function_count"] >= 0
        for fact in out:
            validate_fact(fact.to_dict())
