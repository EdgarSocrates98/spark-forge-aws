"""Golden test do corpus workload: seis cenarios sinteticos do WorkloadFingerprint.

Task 6 do plano `2026-08-28-workload-fingerprint.md`. `sparkforge workload`
NAO extrai de artefato -- classifica facts JA extraidos -- entao cada fixture
tem `input/facts.json` no MOLDE do que `--facts` consome (o formato que
`sparkforge analyze sql-metrics --out` produz), `input/workload.yaml` quando o
cenario declara inventario, e `input/history/*.json` quando o cenario tem
historico: um arquivo de facts por RUN ANTERIOR, a mesma separacao que
`--history` exige (`sparkforge/adapters/_core.py::workload_fingerprint`).

`input/workload.yaml`, quando existe, e passado pelo EXTRATOR de verdade
(`extract_workload_path`, `sparkforge/facts/workload.py`) -- e essa e a unica
extracao real deste modulo golden. `input/facts.json` ja chega em forma de
Fact (kind/subject/measures/attrs), e reconstituido direto, sem extrator: e
exatamente o contrato de `sparkforge workload --facts`, que consome facts que
ALGUEM JA extraiu.

Seis cenarios, cada um provando uma fronteira do fingerprint:

  small_batch_extreme_scan     -- o caso que motivou o documento de origem
  no_history                   -- eixos de volume `unknown`, com o comando
  history_too_short            -- `n=2`: recusa de p99 com o `n` declarado
  declared_only                -- `workload.yaml` sem nenhum fact medido
  declared_source_not_observed -- declaracao que nao bate com o medido
  shuffle_heavy_small_scan     -- o eixo novo separando o que o scan nao separa

Alem dos goldens byte-exatos por cenario, `TestOQueOCorpusInteiroGarante`
verifica as duas garantias que valem sobre o corpus INTEIRO, nao por cenario
isolado: nenhum eixo `measured` sem `evidence`/`basis`, e nenhum eixo
`declared` promovido a `measured` -- a fronteira de que depende o subprojeto
D, que escolhe capacidade em cima deste perfil.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.workload import extract_workload_path
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact
from sparkforge.workload.fingerprint import build_fingerprint

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "workload"

REQUIRED_FIXTURES = {
    "small_batch_extreme_scan",
    "no_history",
    "history_too_short",
    "declared_only",
    "declared_source_not_observed",
    "shuffle_heavy_small_scan",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _facts_from_json(path: Path) -> list[Fact]:
    """Reconstitui Facts de um arquivo no formato que `--facts`/`--history` consomem.

    Sem passar por extrator: o proprio contrato de `sparkforge workload` e
    receber facts que outro verbo JA extraiu (`_core._facts_from_dicts`), e
    `id`/`schema_version` no arquivo -- quando presentes -- sao ignorados, os
    mesmos campos que `Fact` deriva.
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


def _declared_facts(directory: Path) -> list[Fact]:
    """A UNICA extracao real deste modulo: `workload.yaml`, quando existe."""
    workload_yaml = directory / "input" / "workload.yaml"
    if not workload_yaml.is_file():
        return []
    return extract_workload_path(workload_yaml, repo_root=directory / "input")


def _facts(directory: Path) -> list[Fact]:
    measured = _facts_from_json(directory / "input" / "facts.json")
    declared = _declared_facts(directory)
    return sort_facts([*measured, *declared])


def _history(directory: Path) -> list[list[Fact]]:
    hist_dir = directory / "input" / "history"
    if not hist_dir.is_dir():
        return []
    return [_facts_from_json(p) for p in sorted(hist_dir.glob("*.json"))]


def run_fixture(directory: Path) -> dict:
    meta = _meta(directory)
    fingerprint = build_fingerprint(
        _facts(directory),
        job_name=meta["job_name"],
        job_run_id=meta["job_run_id"],
        history=_history(directory),
    )
    return fingerprint.to_dict()


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_fingerprint_matches_golden(self, directory):
        fingerprint = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "fingerprint.json").read_text(encoding="utf-8")
        )
        assert fingerprint == expected

    def test_declared_facts_match_golden(self, directory):
        """So os cenarios com `workload.yaml` tem `expected/facts.json`.

        E o golden do extrator de verdade (`extract_workload_path`), e o que
        da aos tres kinds `workload.*` a cobertura que
        `test_fixtures_kind_coverage.py` cobra.
        """
        declared = _declared_facts(directory)
        expected_path = directory / "expected" / "facts.json"
        if not expected_path.is_file():
            assert not declared, (
                f"{directory.name}: workload.yaml produziu facts sem golden -- "
                "crie expected/facts.json."
            )
            return
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert [f.to_dict() for f in declared] == expected

    def test_every_fact_validates_against_schema(self, directory):
        """Terceiro item que morde entregas anteriores: modulo golden novo sem
        `validate_fact` deixou oito kinds invalidos passarem. Aqui, TODO fact
        que alimenta o fingerprint -- medido e declarado -- passa pelo schema."""
        for fact in _facts(directory):
            validate_fact(fact.to_dict())

    def test_extraction_is_deterministic(self, directory):
        assert [f.to_dict() for f in _declared_facts(directory)] == [
            f.to_dict() for f in _declared_facts(directory)
        ]
        assert run_fixture(directory) == run_fixture(directory)


class TestAdversarial:
    def test_small_batch_is_extreme_only_against_its_own_history(self):
        """O caso que motivou o documento: 80 MB e pequeno, mas e o maior run
        que este job ja teve. Sem o historico do PROPRIO job, nao haveria como
        distinguir isso de um scan qualquer."""
        fingerprint = run_fixture(FIXTURES / "small_batch_extreme_scan")
        eixo = fingerprint["axes"]["scan_intensity"]
        assert eixo["value"] == "extreme"
        assert eixo["confidence"] == "measured"
        assert eixo["basis"] == "history_percentile"

    def test_no_history_names_both_halves_of_the_gap(self):
        fingerprint = run_fixture(FIXTURES / "no_history")
        eixo = fingerprint["axes"]["scan_intensity"]
        assert eixo["missing"] == "history_absent"
        assert "collect glue-job-runs" in eixo["collect_command"]
        assert "analyze sql-metrics" in eixo["collect_command"]
        assert fingerprint["axes"]["skew_risk"]["confidence"] == "measured"
        assert fingerprint["axes"]["file_pressure"]["confidence"] == "measured"

    def test_history_too_short_is_distinct_from_history_absent(self):
        fingerprint = run_fixture(FIXTURES / "history_too_short")
        assert fingerprint["axes"]["scan_intensity"]["missing"] == "history_too_short"

    def test_declared_only_has_no_measured_axis(self):
        fingerprint = run_fixture(FIXTURES / "declared_only")
        for nome, eixo in fingerprint["axes"].items():
            assert eixo["confidence"] != "measured", nome
        assert fingerprint["axes"]["sla_class"]["confidence"] == "declared"

    def test_declared_only_also_proves_the_unresolved_kind(self):
        """A duplicata em `workload.yaml` e o que da a `workload.unresolved`
        cobertura, sem precisar de um setimo cenario."""
        declared = _declared_facts(FIXTURES / "declared_only")
        reasons = {f.attrs.get("reason") for f in declared if f.kind == "workload.unresolved"}
        assert reasons == {"job_declared_twice"}

    def test_declared_source_mismatch_does_not_block_other_axes(self):
        """A recusa e SO do eixo declarado: o scan que existe (de outra fonte)
        continua alimentando `file_pressure` normalmente."""
        fingerprint = run_fixture(FIXTURES / "declared_source_not_observed")
        assert fingerprint["axes"]["primary_input_class"]["missing"] == (
            "declared_source_not_observed"
        )
        assert fingerprint["axes"]["file_pressure"]["confidence"] == "measured"

    def test_shuffle_axis_separates_what_scan_axis_cannot(self):
        fingerprint = run_fixture(FIXTURES / "shuffle_heavy_small_scan")
        assert fingerprint["axes"]["scan_intensity"]["value"] in ("low", "medium")
        assert fingerprint["axes"]["shuffle_intensity"]["value"] == "extreme"


class TestOQueOCorpusInteiroGarante:
    def test_no_measured_axis_without_evidence(self):
        """Eixo `measured` sem evidencia e classe sem lastro.

        Sobre o corpus INTEIRO, e nao por cenario: um default que preenchesse a
        classe sem evidencia passaria em cada cenario isolado e quebraria aqui.
        """
        for directory in fixture_dirs():
            fingerprint = run_fixture(directory)
            for nome, eixo in fingerprint["axes"].items():
                if eixo["confidence"] == "measured":
                    assert eixo["evidence"], (directory.name, nome)
                    assert eixo["basis"], (directory.name, nome)

    def test_no_declared_axis_is_ever_promoted_to_measured(self):
        """A fronteira entre o que alguem escreveu e o que a maquina mediu.

        E dela que depende o subprojeto D, que vai escolher capacidade em cima
        deste perfil e precisa saber em que esta pisando.
        """
        declarados = {"sla_class", "primary_input_class"}
        for directory in fixture_dirs():
            fingerprint = run_fixture(directory)
            for nome in declarados:
                assert fingerprint["axes"][nome]["confidence"] != "measured", (
                    directory.name,
                    nome,
                )
