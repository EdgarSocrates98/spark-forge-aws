"""Golden test do corpus de grafo de chamadas.

Arquivo dedicado porque a fixture nao e extraida, e DERIVADA: `extract_tree`
produz os facts de `pyspark_ast` e `build_call_graph` deriva o grafo a partir
deles. O golden guarda so os derivados -- repetir os de entrada faria uma
mudanca em `pyspark_ast` quebrar dois goldens pelo mesmo motivo, escondendo
qual dos dois contratos regrediu.

Os quatro kinds `callgraph.*` nao alimentam regra nenhuma: quem consome e o
agente `glue-incremental-performance-architect` e a skill
`analyze-library-call-graph`. Fact sem regra e o que some primeiro numa
refatoracao -- ate este corpus existir, os quatro apareciam em ZERO golden.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.call_graph import build_call_graph
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "callgraph"

REQUIRED_FIXTURES = {"mutual_recursion", "linear_pipeline", "library_surface"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    return build_call_graph(facts, path_hint=directory.name)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    derived = _derive(directory)
    findings, skipped = judge(derived, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, derived, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _summary(facts):
    return _by_kind(facts, "callgraph.summary")[0]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_derivation_is_deterministic(self, directory):
        assert [f.to_dict() for f in _derive(directory)] == [
            f.to_dict() for f in _derive(directory)
        ]

    def test_summary_counts_agree_with_the_emitted_facts(self, directory):
        """A sumarizacao nao pode divergir dos facts que ela resume -- e o tipo
        de erro que so aparece quando alguem le o relatorio e a conta nao
        fecha."""
        _, facts, _, _ = run_fixture(directory)
        summary = _summary(facts)
        assert summary.measures["function_count"] == len(_by_kind(facts, "callgraph.function"))
        assert summary.attrs["has_cycle"] == bool(_by_kind(facts, "callgraph.cycle"))


class TestAdversarial:
    def test_cycle_is_detected_and_carries_its_members(self):
        """Uma leitura que aparece UMA vez no codigo, dentro de um ciclo, e
        trabalho repetido em runtime. Sem `contains_spark_work` o ciclo vira
        curiosidade estrutural em vez de achado de performance."""
        _, facts, _, _ = run_fixture(FIXTURES / "mutual_recursion")
        cycle = _by_kind(facts, "callgraph.cycle")[0]
        assert cycle.attrs["functions"] == ["processa_lote", "trata_rejeitados"]
        assert cycle.attrs["contains_spark_work"] is True
        assert cycle.measures["length"] == 2
        assert _summary(facts).attrs["has_cycle"] is True

    def test_acyclic_graph_reports_no_cycle_at_all(self):
        """A metade negativa: um detector que devolvesse "tem ciclo" para
        qualquer grafo passaria em `mutual_recursion` sozinha."""
        _, facts, _, _ = run_fixture(FIXTURES / "linear_pipeline")
        assert _by_kind(facts, "callgraph.cycle") == []
        assert _summary(facts).attrs["has_cycle"] is False

    def test_every_function_is_reachable_from_the_entrypoint(self):
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            summary = _summary(facts)
            assert summary.measures["unreachable_from_entrypoint_count"] == 0, directory.name

    def test_every_defined_function_became_a_node(self):
        """A divida da Fase 1, fechada: o no vem da DEFINICAO, nao da aresta.

        Enquanto `nodes` vinha so das arestas, uma funcao definida e nunca
        chamada nao existia no grafo -- e `unreachable_function_count`, o nome
        antigo da medida, devolvia zero justamente no caso que ele parecia
        medir. Aqui as duas contagens tem que fechar contra os facts
        `pyspark.function_def` que a extracao produziu.
        """
        for directory in fixture_dirs():
            derived = _derive(directory)
            defined = {
                (f.subject["file"], f.subject["symbol"])
                for f in extract_tree(directory / "input", repo_root=directory / "input")
                if f.kind == "pyspark.function_def"
            }
            nodes = {
                (f.subject["file"], f.subject["symbol"])
                for f in _by_kind(derived, "callgraph.function")
            }
            assert defined <= nodes, directory.name
            counted = _summary(derived).measures["defined_function_count"]
            assert counted == len(defined), directory.name

    def test_the_library_surface_yields_exactly_one_unreferenced_symbol(self):
        """A metade negativa da medida, que e a que decide se ela e usavel.

        Oito das nove funcoes de `library_surface` nao tem chamador local e
        NENHUMA delas e sobra: duas estao em `__all__`, uma e chamada
        cross-modulo, uma e callback, uma e decorada, duas sao metodos e uma e
        `main` sob `if __name__`. Se esta lista crescer, a medida passou a
        acusar codigo vivo -- o falso positivo em massa que
        `rules/catalog/README.md` trata como o pior defeito possivel.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "library_surface")
        summary = _summary(facts)
        assert summary.attrs["unreferenced_functions"] == ["_rotina_abandonada"]
        assert summary.measures["unreferenced_function_count"] == 1
        assert summary.measures["opaque_caller_function_count"] == 5

    def test_no_rule_consumes_the_summary(self):
        """`callgraph.summary` segue sem regra DE PROPOSITO (ver o comentario
        final de `rules/catalog/callgraph.yaml`): "sem referencia neste corpus"
        e informacao util para o agente, nao achado. Se alguem escrever uma
        regra sobre ela, este teste quebra e obriga a decisao a ser explicita.
        """
        rules = [
            rule
            for rule in load_catalog()
            if "callgraph.summary" in rule.get("requires_facts", [])
        ]
        assert rules == [], [r["id"] for r in rules]

    def test_spark_work_is_attributed_to_the_entrypoint_that_reaches_it(self):
        """`via` e o caminho, e e o que torna o achado acionavel: sem ele o
        operador sabe que ha uma leitura alcancavel, mas nao por onde."""
        _, facts, _, _ = run_fixture(FIXTURES / "linear_pipeline")
        reachable = _by_kind(facts, "callgraph.reachable_spark_work")
        assert reachable
        for fact in reachable:
            assert fact.attrs["entrypoint"] == "main"
            assert fact.attrs["via"][0] == "main"
