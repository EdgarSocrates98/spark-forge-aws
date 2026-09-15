"""Unidade do Debate ROI Gate (`sparkforge/agentic/executor/gate.py`).

O par real do catalogo (`SF-GRAPH-005` x `SF-LF-001`, so na uniao das duas
fixtures da regra 29) e a base: as variacoes mudam severidade, `kind` ou
evidencia de um finding e conferem o veredito, sem inventar par novo. Onde a
ordem das regras precisa de combinacao que o par real nao tem, o gate e chamado
direto com findings sinteticos.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sparkforge.agentic.executor import gate
from sparkforge.agentic.executor.run import open_debate_plans, run_executor

RAIZ = Path(__file__).resolve().parents[1]
UNIAO = (
    RAIZ / "fixtures" / "graph" / "import_sem_jar_no_iac" / "expected",
    RAIZ / "fixtures" / "infra_code" / "fgac_com_jar_extra" / "expected",
)
RUNTIME = {"glue": "5.0", "spark": "3.5.4"}
BUDGET = {"max_debates": 1, "max_rounds": 3}
POLITICA = {"policy_version": 1, "debate_severities": ["P0", "P1"]}
PLANO = {"participants": [{"agent": "a"}, {"agent": "b"}], "participants_unresolved": []}


def _uniao(overrides: dict[str, dict[str, Any]] | None = None) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    facts: list[dict] = []
    for pasta in UNIAO:
        findings += json.loads((pasta / "findings.json").read_text(encoding="utf-8"))
        facts += json.loads((pasta / "facts.json").read_text(encoding="utf-8"))
    findings = copy.deepcopy(findings)
    for finding in findings:
        for chave, valor in (overrides or {}).get(finding["rule_id"], {}).items():
            if chave == "evidence_append":
                finding["evidence"] = list(finding.get("evidence") or []) + valor
            elif chave == "action":
                finding["action"] = {**finding["action"], **valor}
            else:
                finding[chave] = valor
    return findings, facts


def _gate(overrides: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    findings, facts = _uniao(overrides)
    planos = open_debate_plans(findings, facts, RUNTIME, BUDGET)
    assert len(planos) == 1, planos
    return planos[0]["debate_gate"]


def _resultado(recommendation: str = "experiment", vencedor: str | None = "c1") -> Any:
    return SimpleNamespace(recommendation=recommendation, winning_claim_id=vencedor)


def _finding(rule_id: str, severity: str | None, kind: str) -> dict[str, Any]:
    finding: dict[str, Any] = {"rule_id": rule_id, "action": {"kind": kind}}
    if severity is not None:
        finding["severity"] = severity
    return finding


def _avaliar(findings: list[dict], resultado: Any = None, reversibilidade=None) -> dict:
    return gate.avaliar(
        ("SF-A-001", "SF-B-001"),
        resultado or _resultado(),
        findings,
        [],
        1,
        PLANO,
        politica=POLITICA,
        reversibilidade=reversibilidade or {"k.rev": True, "k.irrev": False},
    )


class TestParReal:
    def test_par_real_sai_debater_pela_severidade(self):
        bloco = _gate()
        assert bloco["verdict"] == "debater"
        assert "severidade:SF-LF-001=P0" in bloco["reasons"]
        assert "severidade:SF-GRAPH-005=P1" in bloco["reasons"]
        assert not any(m.startswith("irreversivel") for m in bloco["reasons"])

    def test_lacuna_citando_o_par_sai_experimentar_antes(self):
        bloco = _gate({"SF-LF-001": {"evidence_append": ["f_ausente_do_case"]}})
        assert bloco["verdict"] == "experimentar_antes"
        assert bloco["reasons"] == ["lacuna_mensuravel"]
        (lacuna,) = bloco["signals"]["evidence_gap"]
        assert lacuna["rules"] == ["SF-LF-001"]
        assert "f_ausente_do_case" in lacuna["question"]
        assert lacuna["experiment"]["variable"]

    def test_par_barato_e_reversivel_sai_nao_debater(self):
        bloco = _gate({"SF-GRAPH-005": {"severity": "P3"}, "SF-LF-001": {"severity": "P3"}})
        assert bloco["verdict"] == "nao_debater"
        assert bloco["reasons"] == ["barato_e_reversivel"]
        assert bloco["signals"]["reversible"] == {"SF-GRAPH-005": True, "SF-LF-001": True}

    def test_kind_fora_do_vocabulario_sai_unresolved(self):
        bloco = _gate(
            {
                "SF-GRAPH-005": {"severity": "P3"},
                "SF-LF-001": {"severity": "P3", "action": {"kind": "dependency.inexistente"}},
            }
        )
        assert bloco["verdict"] == "unresolved"
        assert bloco["missing"] == ["reversible:SF-LF-001"]


class TestOrdem:
    def test_irreversivel_decide_mesmo_com_severidade_ausente(self):
        bloco = _avaliar(
            [_finding("SF-A-001", None, "k.rev"), _finding("SF-B-001", "P3", "k.irrev")]
        )
        assert bloco["verdict"] == "debater"
        assert bloco["reasons"] == ["irreversivel:SF-B-001"]
        assert bloco["missing"] == ["severity:SF-A-001"]

    def test_escalate_sai_debater(self):
        bloco = _avaliar(
            [_finding("SF-A-001", "P3", "k.rev"), _finding("SF-B-001", "P3", "k.rev")],
            _resultado("escalate"),
        )
        assert bloco["verdict"] == "debater"
        assert bloco["reasons"] == ["sem_lastro:escalate"]

    def test_sem_claim_vencedora_conta_como_sem_lastro(self):
        bloco = _avaliar(
            [_finding("SF-A-001", "P3", "k.rev"), _finding("SF-B-001", "P3", "k.rev")],
            _resultado("experiment", vencedor=None),
        )
        assert bloco["verdict"] == "debater"
        assert bloco["signals"]["arbitration"] == "sem_vencedor"

    def test_pior_severidade_da_regra_vence(self):
        bloco = _avaliar(
            [
                _finding("SF-A-001", "P3", "k.rev"),
                _finding("SF-A-001", "P1", "k.rev"),
                _finding("SF-B-001", "P3", "k.rev"),
            ]
        )
        assert bloco["signals"]["severity"] == {"SF-A-001": "P1", "SF-B-001": "P3"}
        assert bloco["verdict"] == "debater"

    def test_severidade_fora_de_p0_p3_e_ausente(self):
        bloco = _avaliar(
            [_finding("SF-A-001", "alta", "k.rev"), _finding("SF-B-001", "P3", "k.rev")]
        )
        assert bloco["verdict"] == "unresolved"
        assert bloco["missing"] == ["severity:SF-A-001"]


class TestSinaisERecusas:
    def test_sinais_informativos_e_ganho_de_informacao_recusado(self):
        bloco = _gate()
        assert bloco["signals"]["complexity"] >= 1
        assert bloco["signals"]["contradiction_count"] == 1
        assert bloco["signals"]["arbitration"] == "experiment"
        assert bloco["refused"]["expected_information_gain"]["reason"].startswith("sem fonte")

    def test_nenhuma_frase_de_ganho_ou_economia(self):
        textos: list[str] = []

        def colher(valor: Any) -> None:
            if isinstance(valor, str):
                textos.append(valor.lower())
            elif isinstance(valor, dict):
                for item in valor.values():
                    colher(item)
            elif isinstance(valor, list):
                for item in valor:
                    colher(item)

        for overrides in (
            None,
            {"SF-LF-001": {"evidence_append": ["f_ausente_do_case"]}},
            {"SF-GRAPH-005": {"severity": "P3"}, "SF-LF-001": {"severity": "P3"}},
        ):
            colher(_gate(overrides))
        proibidas = ("economi", "ganho", "poupa", "saving", "roi ")
        assert not [t for t in textos if any(p in t for p in proibidas)]


class TestPolitica:
    def test_politica_do_catalogo_e_valida(self):
        assert gate.load_policy()["debate_severities"] == ["P0", "P1"]

    @pytest.mark.parametrize(
        "doc",
        [
            [],
            {"debate_severities": ["P0"]},
            {"policy_version": 1, "debate_severities": []},
            {"policy_version": 1, "debate_severities": ["P5"]},
        ],
    )
    def test_politica_malformada_recusa_nomeando_o_campo(self, doc):
        with pytest.raises(gate.GatePolicyError, match="debate_gate.yaml"):
            gate.validate_policy(doc)

    def test_politica_invalida_sai_unresolved_e_nao_derruba_o_plano(self, monkeypatch):
        def quebra(path=None):
            raise gate.GatePolicyError("debate_gate.yaml: quebrada de proposito")

        monkeypatch.setattr(gate, "load_policy", quebra)
        bloco = _gate()
        assert bloco["verdict"] == "unresolved"
        assert bloco["missing"] == ["policy"]
        assert bloco["policy"] == {
            "status": "unresolved",
            "reason": "debate_gate.yaml: quebrada de proposito",
        }

    def test_reversibilidade_do_catalogo_tem_os_setenta(self):
        mapa = gate.load_reversibility()
        assert len(mapa) == 70
        assert all(isinstance(v, bool) for v in mapa.values())


class TestTrace:
    def test_arbitrate_grava_trace_proprio_do_gate(self, tmp_path):
        findings, facts = _uniao()
        run_executor(findings, facts, tmp_path, RUNTIME, BUDGET)
        (arquivo,) = tmp_path.rglob("traces.jsonl")
        traces = [
            json.loads(linha)
            for linha in arquivo.read_text(encoding="utf-8").splitlines()
            if linha
        ]
        por_tipo = {t["kind"]: t for t in traces}
        assert set(por_tipo) == {"arbitration", "debate_gate"}
        assert por_tipo["debate_gate"]["verdict"] == "debater"
        assert por_tipo["debate_gate"]["id"] != por_tipo["arbitration"]["id"]
        assert "verdict" not in por_tipo["arbitration"]
