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

REQUIRED_FIXTURES = {"mutual_recursion", "linear_pipeline"}


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
            assert _summary(facts).measures["unreachable_function_count"] == 0, directory.name

    def test_spark_work_is_attributed_to_the_entrypoint_that_reaches_it(self):
        """`via` e o caminho, e e o que torna o achado acionavel: sem ele o
        operador sabe que ha uma leitura alcancavel, mas nao por onde."""
        _, facts, _, _ = run_fixture(FIXTURES / "linear_pipeline")
        reachable = _by_kind(facts, "callgraph.reachable_spark_work")
        assert reachable
        for fact in reachable:
            assert fact.attrs["entrypoint"] == "main"
            assert fact.attrs["via"][0] == "main"
