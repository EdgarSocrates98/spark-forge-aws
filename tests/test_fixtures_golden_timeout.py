"""Golden test do corpus timeout: oito cenarios sinteticos do diagnostico.

Task 5 do plano `2026-08-29-timeout-intelligence.md`. `timeout_diagnosis` NAO
extrai de artefato -- deriva de facts JA extraidos (`glue.job_run`,
`spark.executor.lost`, `spark.stage.failure`, `spark.conf_effective`) -- mesmo
molde de `fixtures/finops/` e `fixtures/capacity/`, os dominios que tambem
consomem facts em vez de artefato bruto.

A evidencia de cada categoria vem de fonte DIFERENTE, e e por isso que o modulo
existe: nenhum extrator ve as tres juntas.

  wall_clock_sem_event_log    -- o estado do run Glue sozinho
  heartbeat_perdido           -- a frase com que o executor foi removido
  broadcast_estourado         -- a razao da stage que falhou
  network_futures_timeout     -- a mesma fonte, outra frase
  heartbeat_vence_wall_clock  -- os dois sinais, e a precedencia declarada
  timeout_com_spill_e_skew    -- `SF-TIMEOUT-001` dispara
  heartbeat_maior_que_network -- `SF-TIMEOUT-002` dispara
  timeout_sem_evidencia       -- nenhuma regra dispara, e a lacuna e nomeada

Alem dos goldens byte-exatos por cenario, `TestOQueOCorpusInteiroGarante`
verifica as QUATRO garantias que valem sobre o corpus INTEIRO, cada uma contra
um erro concreto que passaria despercebido cenario a cenario:

  1. Todo diagnostico carrega `basis` e a frase literal que o produziu.
  2. Nenhum diagnostico existe sem sinal de timeout na entrada.
  3. Nada no corpus recomenda um valor novo de timeout.
  4. Todo fact emitido valida contra o schema.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.timeout_diagnosis import extract_timeout_diagnosis
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "timeout"

REQUIRED_FIXTURES = {
    "wall_clock_sem_event_log",
    "heartbeat_perdido",
    "broadcast_estourado",
    "network_futures_timeout",
    "heartbeat_vence_wall_clock",
    "timeout_com_spill_e_skew",
    "heartbeat_maior_que_network",
    "timeout_sem_evidencia",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _input_facts(directory: Path) -> list[Fact]:
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


def _derived_facts(directory: Path) -> list[Fact]:
    """A extracao real deste modulo, sobre o pool do proprio fixture."""
    return extract_timeout_diagnosis(_input_facts(directory), "<facts>")


def _facts(directory: Path) -> list[Fact]:
    return sort_facts([*_input_facts(directory), *_derived_facts(directory)])


def run_fixture(directory: Path):
    meta = _meta(directory)
    return judge(_facts(directory), load_catalog(), meta["runtime"])


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_derived_facts_match_golden(self, directory):
        """O golden dos tres kinds `spark.timeout.*` que
        `test_fixtures_kind_coverage.py` cobra."""
        derivados = _derived_facts(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in derivados] == expected

    def test_findings_match_golden(self, directory):
        achados = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in achados] == expected

    def test_every_fact_validates_against_schema(self, directory):
        """Ausencia de `validate_fact` num modulo golden novo ja deixou oito
        kinds invalidos passarem numa entrega anterior."""
        for fact in _derived_facts(directory):
            validate_fact(fact.to_dict())

    def test_meta_declares_what_the_scenario_proves(self, directory):
        meta = _meta(directory)
        assert meta["name"] == directory.name
        assert meta["proves"].strip()


class TestOQueOCorpusInteiroGarante:
    def test_every_diagnosis_carries_basis_and_the_literal_phrase(self):
        """Categoria sem a frase que a produziu e opiniao."""
        vistos = 0
        for directory in fixture_dirs():
            for fact in _derived_facts(directory):
                if fact.kind != "spark.timeout.diagnosis":
                    continue
                assert fact.attrs["basis"], directory.name
                assert fact.attrs["evidence_text"].strip(), directory.name
                vistos += 1
        assert vistos >= 5

    def test_no_diagnosis_without_a_timeout_signal_in_the_input(self):
        """Diagnostico sobre run saudavel seria categoria inventada."""
        for directory in fixture_dirs():
            entradas = _input_facts(directory)
            tem_sinal = any(
                str(f.attrs.get("state") or "").upper() == "TIMEOUT"
                or "timed out" in str(f.attrs.get("reason") or "").lower()
                or "could not execute broadcast" in str(f.attrs.get("reason") or "").lower()
                for f in entradas
            )
            diagnosticos = [
                f for f in _derived_facts(directory) if f.kind == "spark.timeout.diagnosis"
            ]
            if diagnosticos:
                assert tem_sinal, directory.name

    def test_nothing_recommends_a_new_timeout_value(self):
        """Derivar valor de configuracao e o criterio 17, outro subprojeto.

        Sem esta garantia, a proxima pessoa a mexer aqui vai achar que sugerir
        `spark.network.timeout=300s` era o objetivo.
        """
        for directory in fixture_dirs():
            blob = str([f.to_dict() for f in _derived_facts(directory)]).lower()
            for palavra in ("suggested_value", "recommended_value", "novo_valor"):
                assert palavra not in blob, (directory.name, palavra)

    def test_the_two_rules_are_reached_by_the_corpus(self):
        """Regra sem golden que dispara e regra que ninguem exercita."""
        disparadas = set()
        for directory in fixture_dirs():
            disparadas.update(f.rule_id for f in run_fixture(directory))

        assert {"SF-TIMEOUT-001", "SF-TIMEOUT-002"} <= disparadas
