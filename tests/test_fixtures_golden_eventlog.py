"""Golden test do corpus de fixtures de event log.

Arquivo dedicado, separado de `test_fixtures_golden.py`. Aquele modulo esta
fortemente acoplado ao corpus PySpark: `REQUIRED_FIXTURES` e um conjunto
fechado de nomes, e `run_fixture` chama `extract_tree`, que caminha um
diretorio inteiro em busca de `*.py`. Uma fixture de event log e um unico
arquivo `*.jsonl` (nao uma arvore de modulos Python) extraido por
`extract_event_log_path`, nao por `extract_tree`. Encaixar as duas fontes no
mesmo helper exigiria ramificar `run_fixture` por tipo de fixture ou afrouxar
`REQUIRED_FIXTURES` para um superconjunto -- em ambos os casos o teste PySpark
existente fica mais fraco para servir a um formato de entrada diferente.
Um arquivo irmao, mesma estrutura de asserts, preserva os dois testes
igualmente rigorosos sem acoplar os dois formatos de fixture.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "eventlog"

# Os dois ultimos sao os pares de `skewed_stage` nos ramos de `severity_by`:
# `skewed_stage` so tem razoes muito acima do primeiro ramo (15 contra 10 em
# SF-UI-001, 0.316 contra 0.20 em SF-UI-004), entao os ramos P2 das duas regras
# nao apareciam em golden nenhum -- podiam virar qualquer severidade com a
# suite inteira verde. Cada um traz o valor no limiar EXATO da regra e o vizinho
# logo abaixo, que nao dispara.
REQUIRED_FIXTURES = {
    "skewed_stage",
    "rolling_parts_version_conflict",
    "duration_skew_at_threshold",
    "gc_pressure_at_threshold",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for jsonl in sorted(input_dir.glob("*.jsonl")):
        facts.extend(extract_event_log_path(jsonl, repo_root=input_dir))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


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

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second


class TestAdversarial:
    def test_malformed_line_reported_not_silently_dropped(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        unresolved = [f for f in facts if f.kind == "spark.unresolved"]
        assert unresolved
        assert unresolved[0].attrs["reason"] == "malformed_json"

    def test_executor_lost_without_heap_oom_is_classified_as_container(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        lost = [f for f in facts if f.kind == "spark.executor.lost"]
        assert lost
        assert lost[0].attrs["heap_oom_in_log"] is False
        assert "OutOfMemoryError" not in lost[0].attrs["reason"]

    def test_healthy_stage_has_no_duration_skew(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "skewed_stage")
        healthy = next(
            f
            for f in facts
            if f.kind == "spark.stage.task_duration"
            and f.subject["symbol"] == "stage_healthy_read"
        )
        ratio = healthy.measures["max_ms"] / healthy.measures["p50_ms"]
        assert ratio < 3.0

    def _stage(self, facts, kind, symbol):
        return next(
            f for f in facts if f.kind == kind and f.subject["symbol"] == symbol
        )

    def test_both_severity_branches_of_the_duration_skew_rule_have_a_fixture(self):
        """Os dois ramos de SF-UI-001, e o limiar que decide entre eles.

        `skewed_stage` tem razao 15 e cai no primeiro ramo;
        `duration_skew_at_threshold` tem razao 3.0 -- o proprio
        `threshold.ratio` da regra -- e cai no segundo. Antes do segundo fixture
        o ramo P2 nao aparecia em golden nenhum: a severidade dele podia virar
        qualquer valor com a suite inteira verde, porque 15 esta longe demais do
        10 do primeiro ramo para os dois se distinguirem.

        O stage vizinho, com 2900 ms em vez de 3000, NAO e acusado: e o lado
        negativo do limiar, sem o qual a regra poderia estar disparando pela
        mera presenca do fact.

        Os numeros vem do CATALOGO, nunca repetidos aqui: um limiar escrito em
        dois lugares vira dois limiares no dia em que alguem ajustar so um.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-UI-001")
        agudo, moderado = regra["severity_by"]
        limiar_do_ramo = float(agudo["when"].rsplit(">=", 1)[1])

        _, agudo_facts, findings_agudo, _ = run_fixture(FIXTURES / "skewed_stage")
        _, limiar_facts, findings_limiar, _ = run_fixture(
            FIXTURES / "duration_skew_at_threshold"
        )

        torto = self._stage(agudo_facts, "spark.stage.task_duration", "stage_skewed_join")
        no_limiar = self._stage(
            limiar_facts, "spark.stage.task_duration", "stage_shuffle_skew_at_threshold"
        )
        abaixo = self._stage(
            limiar_facts, "spark.stage.task_duration", "stage_shuffle_below_threshold"
        )

        assert torto.measures["max_ms"] / torto.measures["p50_ms"] >= limiar_do_ramo
        razao_no_limiar = no_limiar.measures["max_ms"] / no_limiar.measures["p50_ms"]
        razao_abaixo = abaixo.measures["max_ms"] / abaixo.measures["p50_ms"]
        assert razao_no_limiar == regra["threshold"]["ratio"]
        assert razao_no_limiar < limiar_do_ramo
        assert razao_abaixo < regra["threshold"]["ratio"]

        achado_agudo = next(f for f in findings_agudo if f.rule_id == "SF-UI-001")
        achados_limiar = [f for f in findings_limiar if f.rule_id == "SF-UI-001"]
        assert achado_agudo.severity == agudo["severity"]
        # Um achado so: o stage vizinho fica de fora, e e ele que prova o limiar.
        assert [f.subject["symbol"] for f in achados_limiar] == [
            "stage_shuffle_skew_at_threshold"
        ]
        assert achados_limiar[0].severity == moderado["severity"]

    def test_duration_skew_at_threshold_has_no_input_skew(self):
        """O que separa SF-UI-001 de SF-UI-002, no mesmo stage.

        As oito tasks leem o MESMO numero de bytes de input; a lenta e lenta por
        ler 3x mais bytes de shuffle remoto. Se o corpus so tivesse stage onde a
        task lenta tambem le mais input, uma regra que confundisse os dois eixos
        passaria despercebida.
        """
        _, facts, findings, _ = run_fixture(FIXTURES / "duration_skew_at_threshold")
        entrada = self._stage(
            facts, "spark.stage.task_input", "stage_shuffle_skew_at_threshold"
        )
        assert entrada.measures["max_bytes"] == entrada.measures["p50_bytes"]
        assert "SF-UI-002" not in {f.rule_id for f in findings}

    def test_both_severity_branches_of_the_gc_rule_have_a_fixture(self):
        """Os dois ramos de SF-UI-004, e o limiar que decide entre eles.

        Mesma estrutura do teste de SF-UI-001: `skewed_stage` tem 0.316 e cai no
        primeiro ramo, `gc_pressure_at_threshold` tem 0.15 -- o proprio
        `threshold.ratio` -- e cai no segundo, e o stage vizinho com 0.14 nao e
        acusado.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-UI-004")
        agudo, moderado = regra["severity_by"]
        limiar_do_ramo = float(agudo["when"].rsplit(">=", 1)[1])

        _, agudo_facts, findings_agudo, _ = run_fixture(FIXTURES / "skewed_stage")
        _, limiar_facts, findings_limiar, _ = run_fixture(
            FIXTURES / "gc_pressure_at_threshold"
        )

        pesado = self._stage(agudo_facts, "spark.stage.gc", "stage_skewed_join")
        no_limiar = self._stage(limiar_facts, "spark.stage.gc", "stage_gc_at_threshold")
        abaixo = self._stage(limiar_facts, "spark.stage.gc", "stage_gc_below_threshold")

        assert pesado.measures["gc_ms"] / pesado.measures["executor_run_ms"] >= limiar_do_ramo
        razao_no_limiar = no_limiar.measures["gc_ms"] / no_limiar.measures["executor_run_ms"]
        razao_abaixo = abaixo.measures["gc_ms"] / abaixo.measures["executor_run_ms"]
        assert razao_no_limiar == regra["threshold"]["ratio"]
        assert razao_no_limiar < limiar_do_ramo
        assert razao_abaixo < regra["threshold"]["ratio"]

        achado_agudo = next(f for f in findings_agudo if f.rule_id == "SF-UI-004")
        achados_limiar = [f for f in findings_limiar if f.rule_id == "SF-UI-004"]
        assert achado_agudo.severity == agudo["severity"]
        assert [f.subject["symbol"] for f in achados_limiar] == ["stage_gc_at_threshold"]
        assert achados_limiar[0].severity == moderado["severity"]

    def test_skipped_stage_has_zero_task_count(self):
        _, facts, _, _ = run_fixture(FIXTURES / "skewed_stage")
        skipped_stage = next(
            f
            for f in facts
            if f.kind == "spark.stage.task_count"
            and f.subject["symbol"] == "stage_skipped_cached"
        )
        assert skipped_stage.measures["task_count"] == 0
