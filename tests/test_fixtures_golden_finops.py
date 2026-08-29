"""Golden test do corpus finops: nove cenarios sinteticos do relatorio financeiro.

Task 6 do plano `2026-08-28-finops-run-cost.md`. `sparkforge finops` NAO extrai de
artefato -- compoe sobre facts JA extraidos (`glue.job_run`, `workload.declared`,
sintomas) -- mesmo molde de `fixtures/capacity/` e
`tests/test_fixtures_golden_capacity.py`, o dominio mais parecido porque tambem
consome facts em vez de artefato bruto.

A UNICA extracao real deste modulo e `extract_run_cost` (`sparkforge/facts/
run_cost.py`), chamada aqui sobre os `glue.job_run` do proprio fixture para produzir
`expected/facts.json` -- o golden dos dois kinds `glue.run_cost*` que
`test_fixtures_kind_coverage.py` cobra. `build_finops_report` chama o MESMO extrator
por dentro; os dois caminhos usam a mesma funcao, entao nao podem divergir.

Nove cenarios, cada um provando uma fronteira do relatorio:

  cost_from_derived_dpu      -- custo sobre DPU derivado, `dpu_source` propagado
  cost_from_observed_dpu     -- custo sobre `DPUSeconds` medido
  no_dpu_no_cost              -- Auto Scaling sem `DPUSeconds`: lacuna, nao zero
  more_resource_costs_less   -- o dobro de workers custando menos
  more_resource_costs_more   -- o mesmo eixo no sentido oposto
  cheap_but_misses_sla       -- mais barata por run, mais cara por desfecho
  cost_is_in_the_code        -- achados de codigo: a alavanca nao e worker
  no_lever_found              -- sem achado e com capacidade dimensionada
  no_cloudwatch                -- custo sai, sintoma de utilizacao ausente

Alem dos goldens byte-exatos por cenario, `TestOQueOCorpusInteiroGarante` verifica
as QUATRO garantias que valem sobre o corpus INTEIRO, nao por cenario isolado --
cada uma existe contra um erro concreto que passaria despercebido cenario a
cenario:

  1. Todo fact de custo carrega as duas ressalvas (`region`, `runtime_version`).
  2. Nenhum fact de custo existe sem `dpu_seconds` medido.
  3. Achado de codigo nunca aparece sob a alavanca de capacidade.
  4. Nada na saida atribui custo a uma causa.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact, Finding, sort_facts
from sparkforge.findings.validate import validate_fact
from sparkforge.finops import build_finops_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "finops"

REQUIRED_FIXTURES = {
    "cost_from_derived_dpu",
    "cost_from_observed_dpu",
    "no_dpu_no_cost",
    "more_resource_costs_less",
    "more_resource_costs_more",
    "cheap_but_misses_sla",
    "cost_is_in_the_code",
    "no_lever_found",
    "no_cloudwatch",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _input_facts(directory: Path) -> list[Fact]:
    """Os facts que `sparkforge finops` consome, no molde de `--facts`.

    Sem passar por extrator: `id`/`schema_version` no arquivo -- quando
    presentes -- sao ignorados, os mesmos campos que `Fact` deriva.
    """
    data = json.loads((directory / "input" / "facts.json").read_text(encoding="utf-8"))
    return [
        Fact(
            kind=d["kind"],
            subject=d["subject"],
            measures=d.get("measures", {}),
            attrs=d.get("attrs", {}),
            provenance=d.get("provenance", {}),
        )
        for d in data
    ]


def _findings(directory: Path) -> list[Finding]:
    path = directory / "input" / "findings.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Finding(
            rule_id=d["rule_id"],
            title=d["title"],
            severity=d["severity"],
            confidence=d["confidence"],
            status=d["status"],
            subject=d["subject"],
            evidence=d["evidence"],
        )
        for d in data
    ]


def _cost_facts(directory: Path) -> list[Fact]:
    """A UNICA extracao real deste modulo: `extract_run_cost` sobre os
    `glue.job_run` do fixture -- o mesmo caminho que `build_finops_report`
    percorre por dentro."""
    runs = [f for f in _input_facts(directory) if f.kind == "glue.job_run"]
    return extract_run_cost(runs, "<facts>")


def _facts(directory: Path) -> list[Fact]:
    """Todo fact que o corpus deste dominio produz ou consome: entrada e
    custo. As garantias do corpus inteiro iteram sobre esta lista."""
    return sort_facts([*_input_facts(directory), *_cost_facts(directory)])


def run_fixture(directory: Path) -> dict:
    meta = _meta(directory)
    return build_finops_report(
        _input_facts(directory), job_name=meta["job_name"], findings=_findings(directory)
    )


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_report_matches_golden(self, directory):
        relatorio = run_fixture(directory)
        expected = json.loads((directory / "expected" / "report.json").read_text(encoding="utf-8"))
        assert relatorio == expected

    def test_cost_facts_match_golden(self, directory):
        """O golden do extrator de verdade -- da aos dois kinds `glue.run_cost*`
        a cobertura que `test_fixtures_kind_coverage.py` cobra."""
        custos = _cost_facts(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in custos] == expected

    def test_every_fact_validates_against_schema(self, directory):
        """Ausencia de `validate_fact` num modulo golden novo ja deixou oito
        kinds invalidos passarem numa entrega anterior. Aqui, TODO fact --
        entrada e custo -- passa pelo schema."""
        for fact in _facts(directory):
            validate_fact(fact.to_dict())

    def test_report_is_deterministic(self, directory):
        assert run_fixture(directory) == run_fixture(directory)


class TestAdversarial:
    def test_more_resource_costs_less_in_this_direction(self):
        relatorio = run_fixture(FIXTURES / "more_resource_costs_less")
        linhas = {c["number_of_workers"]: c for c in relatorio["frontier"]}
        assert linhas[20]["cost_per_run_p95"] < linhas[10]["cost_per_run_p95"]

    def test_more_resource_costs_more_in_the_opposite_direction(self):
        """O contrafactual do cenario anterior: sem este, o corpus provaria
        so que mais recurso custa menos, quando a troca recurso-tempo pode
        ir nos dois sentidos."""
        relatorio = run_fixture(FIXTURES / "more_resource_costs_more")
        linhas = {c["number_of_workers"]: c for c in relatorio["frontier"]}
        assert linhas[20]["cost_per_run_p95"] > linhas[10]["cost_per_run_p95"]

    def test_no_dpu_no_cost_is_a_gap_not_a_zero(self):
        relatorio = run_fixture(FIXTURES / "no_dpu_no_cost")
        assert relatorio["frontier"] == []
        assert any(r["reason"] == "cost_unobservable" for r in relatorio["refused"])
        custos = _cost_facts(FIXTURES / "no_dpu_no_cost")
        assert custos and all(f.kind == "glue.run_cost.unresolved" for f in custos)

    def test_dpu_source_is_derived_when_the_run_has_no_measured_dpu(self):
        custos = _cost_facts(FIXTURES / "cost_from_derived_dpu")
        assert custos and all(f.attrs["dpu_source"] == "derived" for f in custos)

    def test_dpu_source_is_observed_when_the_run_carries_dpu_seconds(self):
        custos = _cost_facts(FIXTURES / "cost_from_observed_dpu")
        assert custos and all(f.attrs["dpu_source"] == "observed" for f in custos)

    def test_cheap_by_run_can_be_costly_by_outcome(self):
        relatorio = run_fixture(FIXTURES / "cheap_but_misses_sla")
        mais_barata_por_run = relatorio["frontier"][0]
        mais_barata_por_desfecho = relatorio["per_sla_outcome"][0]
        assert (
            mais_barata_por_run["number_of_workers"]
            != mais_barata_por_desfecho["number_of_workers"]
        )

    def test_code_findings_never_sit_under_the_capacity_lever(self):
        relatorio = run_fixture(FIXTURES / "cost_is_in_the_code")
        assert {f["rule_id"] for f in relatorio["levers"]["code"]["findings"]} == {
            "SF-PY-004",
            "SF-PQ-002",
        }
        assert "SF-PY-004" not in str(relatorio["levers"]["capacity"])
        assert "SF-PQ-002" not in str(relatorio["levers"]["capacity"])

    def test_no_lever_found_is_an_answer_not_a_gap(self):
        relatorio = run_fixture(FIXTURES / "no_lever_found")
        assert relatorio["levers"]["none_found"] is True
        assert relatorio["frontier"]
        assert relatorio["per_sla_outcome"]

    def test_no_cloudwatch_leaves_cost_intact_and_drops_only_the_utilization_symptom(self):
        relatorio = run_fixture(FIXTURES / "no_cloudwatch")
        assert relatorio["frontier"]
        assert "worker_utilization_p50" not in relatorio["symptoms"]
        assert "bytes_read" in relatorio["symptoms"]


class TestOQueOCorpusInteiroGarante:
    def test_every_cost_fact_carries_both_caveats(self):
        """Um fact de custo sem ressalva e um numero que parece preciso."""
        for directory in fixture_dirs():
            for fact in _facts(directory):
                if fact.kind != "glue.run_cost":
                    continue
                assert fact.attrs["region"], directory.name
                assert fact.attrs["runtime_version"], directory.name

    def test_no_cost_fact_exists_without_measured_dpu(self):
        """Custo sobre DPU ausente seria zero disfarcado."""
        for directory in fixture_dirs():
            for fact in _facts(directory):
                if fact.kind == "glue.run_cost":
                    assert fact.measures.get("dpu_seconds"), directory.name

    def test_no_code_finding_under_the_capacity_lever(self):
        """Sugerir troca de worker para um SF-PY e comprar saida de um defeito."""
        for directory in fixture_dirs():
            relatorio = run_fixture(directory)
            capacidade = str(relatorio["levers"]["capacity"])
            for achado in relatorio["levers"]["code"]["findings"]:
                assert achado["rule_id"] not in capacidade, directory.name

    def test_nothing_attributes_cost_to_a_cause(self):
        """A garantia de 3.3, sobre o corpus inteiro.

        Sem ela, a proxima pessoa a mexer aqui vai achar que atribuir e o
        objetivo.
        """
        for directory in fixture_dirs():
            blob = str(run_fixture(directory)).lower()
            for palavra in ("desperd", "waste", "estimated_saving", "economia"):
                assert palavra not in blob, (directory.name, palavra)
