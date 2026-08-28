"""Golden test do corpus capacity: seis cenarios sinteticos da escolha de capacidade sob SLA.

Task 4 do plano `2026-08-28-capacity-sla-optimizer.md`. `sparkforge capacity`
NAO extrai de artefato -- classifica facts JA extraidos -- entao cada fixture
tem `input/facts.json` no molde do que `--facts` consome (`workload.declared`
e `spark.sql.scan` do run CORRENTE) e `input/history/<run>.json`, um arquivo
por RUN ANTERIOR, cada um com exatamente UM `glue.job_run` e os
`spark.sql.scan` daquele run -- a mesma separacao que `--history` exige
(`sparkforge/adapters/_core.py`). Mesmo molde de `fixtures/workload/` e
`tests/test_fixtures_golden_workload.py`, o dominio mais parecido porque
tambem consome facts em vez de artefato bruto.

Seis cenarios, cada um provando uma fronteira do `CapacityPlan`:

  cheapest_that_fits               -- tres capacidades, duas cabem, escolhe a
                                       mais barata -- nao a mais rapida
  none_fits                        -- `chosen: None`, com o quanto cada uma erra
  resolution_too_coarse            -- alvo de 99% com poucos runs: recusa, nao
                                       aprovacao fragil
  volume_filter_changes_the_answer -- a capacidade que ganharia com o
                                       historico inteiro perde ao comparar so
                                       o comparavel
  autoscaling_without_cost         -- capacidade sem `dpu_seconds` medido sai
                                       da comparacao
  single_capacity_observed         -- sem alternativa, e o plano diz isso

Alem dos goldens byte-exatos por cenario, `TestOQueOCorpusInteiroGarante`
verifica as QUATRO garantias que valem sobre o corpus INTEIRO, nao por
cenario isolado -- um erro de ordenacao ou de limiar passaria em cada cenario
isolado e so quebraria aqui.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.capacity import build_capacity_plan
from sparkforge.findings.models import Fact
from sparkforge.findings.validate import validate_fact

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "capacity"

REQUIRED_FIXTURES = {
    "cheapest_that_fits",
    "none_fits",
    "resolution_too_coarse",
    "volume_filter_changes_the_answer",
    "autoscaling_without_cost",
    "single_capacity_observed",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _facts_from_json(path: Path) -> list[Fact]:
    """Reconstitui Facts do formato que `--facts`/`--history` consomem.

    Sem passar por extrator: `sparkforge capacity` recebe facts que outro
    verbo JA extraiu, e `id`/`schema_version` no arquivo -- quando presentes
    -- sao ignorados, os mesmos campos que `Fact` deriva.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
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


def _facts(directory: Path) -> list[Fact]:
    return _facts_from_json(directory / "input" / "facts.json")


def _history(directory: Path) -> list[list[Fact]]:
    hist_dir = directory / "input" / "history"
    if not hist_dir.is_dir():
        return []
    return [_facts_from_json(p) for p in sorted(hist_dir.glob("*.json"))]


def run_fixture(directory: Path) -> dict:
    meta = _meta(directory)
    plano = build_capacity_plan(
        _facts(directory),
        job_name=meta["job_name"],
        job_run_id=meta["job_run_id"],
        history=_history(directory),
    )
    return plano.to_dict()


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_plan_matches_golden(self, directory):
        plano = run_fixture(directory)
        expected = json.loads((directory / "expected" / "plan.json").read_text(encoding="utf-8"))
        assert plano == expected

    def test_every_fact_validates_against_schema(self, directory):
        for fact in [*_facts(directory), *(f for run in _history(directory) for f in run)]:
            validate_fact(fact.to_dict())

    def test_plan_is_deterministic(self, directory):
        assert run_fixture(directory) == run_fixture(directory)


class TestAdversarial:
    def test_cheapest_that_fits_picks_the_middle_not_the_fastest(self):
        plano = run_fixture(FIXTURES / "cheapest_that_fits")
        assert plano["chosen"]["worker_type"] == "G.2X"
        assert plano["chosen"]["number_of_workers"] == 10
        # A mais cara (G.2X x20) tambem e a mais rapida no historico -- e nao
        # foi ela a escolhida.
        mais_cara = max(plano["candidates"], key=lambda c: c["dpu_seconds_p95"])
        assert mais_cara["worker_type"] == "G.2X"
        assert mais_cara["number_of_workers"] == 20
        assert plano["chosen"] != mais_cara

    def test_none_fits_shows_how_far_each_one_missed(self):
        plano = run_fixture(FIXTURES / "none_fits")
        assert plano["chosen"] is None
        assert len(plano["candidates"]) == 3
        assert all(c["meets_sla"] is False for c in plano["candidates"])
        assert all(c["reliability"] == 0.0 for c in plano["candidates"])

    def test_resolution_too_coarse_refuses_a_target_finer_than_the_evidence(self):
        plano = run_fixture(FIXTURES / "resolution_too_coarse")
        assert plano["chosen"] is None
        candidato = plano["candidates"][0]
        assert candidato["reliability"] == 1.0
        assert candidato["meets_sla"] is False
        recusa = [r for r in plano["refused"] if r["reason"] == "resolution_too_coarse"][0]
        assert recusa["runs_comparable"] == 28
        assert recusa["runs_needed"] >= 100

    def test_volume_filter_shows_both_counts_and_flips_the_choice(self):
        plano = run_fixture(FIXTURES / "volume_filter_changes_the_answer")
        perderia = next(c for c in plano["candidates"] if c["worker_type"] == "G.2X")
        ganha = next(c for c in plano["candidates"] if c["worker_type"] == "G.4X")

        # A prova central do cenario: as duas contagens sao DIFERENTES para o
        # candidato que perde, e so a filtrada conta.
        assert perderia["runs_total"] == 20
        assert perderia["runs_comparable"] == 5
        assert perderia["runs_total"] != perderia["runs_comparable"]
        assert perderia["meets_sla"] is False

        # E mais barata por run e AINDA ASSIM nao e a escolhida.
        assert perderia["dpu_seconds_p95"] < ganha["dpu_seconds_p95"]
        assert plano["chosen"]["worker_type"] == "G.4X"

    def test_autoscaling_without_cost_is_refused_not_ranked(self):
        plano = run_fixture(FIXTURES / "autoscaling_without_cost")
        assert [r["reason"] for r in plano["refused"]] == ["cost_unobservable"]
        assert all(c["autoscaling"] is False for c in plano["candidates"])

    def test_single_capacity_observed_says_there_is_nothing_to_compare(self):
        plano = run_fixture(FIXTURES / "single_capacity_observed")
        assert len(plano["candidates"]) == 1
        assert plano["chosen"] is not None
        assert plano["only_one_capacity_observed"] is True


class TestOQueOCorpusInteiroGarante:
    def test_never_chooses_a_costlier_candidate_that_also_fits(self):
        """O objetivo do paragrafo 18: a mais barata que cabe.

        Um erro de ordenacao passaria em cada cenario isolado.
        """
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            if plano["chosen"] is None:
                continue
            cabem = [c for c in plano["candidates"] if c["meets_sla"]]
            assert plano["chosen"]["dpu_seconds_p95"] == min(
                c["dpu_seconds_p95"] for c in cabem
            ), directory.name

    def test_never_chooses_a_candidate_that_misses_the_sla(self):
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            if plano["chosen"] is not None:
                assert plano["chosen"]["meets_sla"] is True, directory.name

    def test_every_approved_candidate_has_the_resolution_to_say_so(self):
        """A garantia que separa "medimos que cabe" de "nao temos como saber"."""
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            alvo = plano["reliability_target"]
            if alvo is None:
                continue
            for candidato in plano["candidates"]:
                if candidato["meets_sla"]:
                    assert candidato["resolution"] <= 1 - alvo, (
                        directory.name,
                        candidato,
                    )

    def test_no_candidate_is_ever_anything_but_review(self):
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            for candidato in plano["candidates"]:
                assert candidato["safety"] == "REVIEW", directory.name
