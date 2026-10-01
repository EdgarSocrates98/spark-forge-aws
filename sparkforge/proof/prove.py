"""Montagem da prova: seleciona os findings aplicados e da a cada um as
obrigacoes de resolucao e de eixo.

`--applied SF-X` aplica todos os findings da regra; `--applied SF-X:simbolo`
so o de `subject.symbol` igual. Mais de um finding selecionado torna a
atribuicao compartilhada: separar o delta de bench entre mudancas exigiria o
run que nao aconteceu (regra 13), entao as obrigacoes de bench saem
`inconclusive`. Resolucao e correcao continuam por finding.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.proof.axis import bench_outcome, funcval_outcome, none_outcome
from sparkforge.proof.keys import stable_key
from sparkforge.proof.resolution import resolve

OUTCOMES = ("refuted", "not_refuted", "inconclusive", "unproven")
VEREDICTOS = ("SF-FVAL-", "SF-BENCH-")
REFUSED: tuple[dict[str, str], ...] = (
    {"field": "proven", "reason": "nenhuma_medida_do_pacote_prova_equivalencia_ou_melhoria"},
    {"field": "gain_estimate", "reason": "exige_o_run_que_nao_aconteceu_regra_13"},
)


def select_applied(
    findings: Sequence[Mapping[str, Any]], applied: Sequence[str]
) -> tuple[list[Mapping[str, Any]], list[dict[str, str]]]:
    """Os findings aplicados, e o que foi pedido e nao existe."""
    selecionados: list[Mapping[str, Any]] = []
    vistos: set[int] = set()
    unresolved: list[dict[str, str]] = []
    for pedido in applied:
        rule_id, _, simbolo = str(pedido).partition(":")
        achados = [
            (indice, f)
            for indice, f in enumerate(findings)
            if f.get("rule_id") == rule_id
            and (not simbolo or str((f.get("subject") or {}).get("symbol") or "") == simbolo)
        ]
        if not achados:
            unresolved.append({"field": f"applied.{pedido}", "reason": "applied_nao_encontrado"})
        for indice, finding in achados:
            if indice not in vistos:
                vistos.add(indice)
                selecionados.append(finding)
    return selecionados, unresolved


def kinds_in_when(clause: Any) -> set[str]:
    """Os kinds que a condicao de uma regra le, varrendo o `when` inteiro."""
    if isinstance(clause, Mapping):
        proprios = {str(clause["fact"])} if isinstance(clause.get("fact"), str) else set()
        return proprios.union(*(kinds_in_when(v) for v in clause.values()))
    if isinstance(clause, list):
        return set().union(*(kinds_in_when(v) for v in clause))
    return set()


def _bench_da_uniao(
    union: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    deltas = sorted(
        (f for f in union if f.get("kind") == "bench.run_delta"), key=lambda f: str(f.get("id"))
    )
    furos = [f.get("attrs") or {} for f in union if f.get("kind") == "bench.unresolved"]
    return (deltas[0].get("measures") or {}) if deltas else None, furos


def _obrigacoes_de_eixo(
    finding: Mapping[str, Any],
    policy: Mapping[str, Any],
    verdicts: set[str],
    funcval_analyzed: bool,
    run_delta: Mapping[str, Any] | None,
    furos: Sequence[Mapping[str, Any]],
    shared: bool,
) -> list[dict[str, Any]]:
    obrigacoes: list[dict[str, Any]] = []
    for eixo in (finding.get("action") or {}).get("moves") or []:
        spec = policy["axes"].get(eixo)
        fonte = (spec or {}).get("source")
        if fonte == "funcval":
            obrigacoes.append(funcval_outcome(eixo, verdicts, funcval_analyzed))
        elif fonte == "bench":
            obrigacoes.append(bench_outcome(eixo, spec, verdicts, run_delta, furos, shared))
        else:
            obrigacoes.append(none_outcome(eixo, spec))
    return obrigacoes


def prove(
    applied_findings: Sequence[Mapping[str, Any]],
    union_verdicts: Sequence[Mapping[str, Any]],
    union_facts: Sequence[Mapping[str, Any]],
    after_findings: Sequence[Mapping[str, Any]],
    after_skipped: Sequence[Mapping[str, Any]],
    after_facts: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    rules_by_id: Mapping[str, Mapping[str, Any]],
    emitted_by: Mapping[str, str],
    unresolved: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    """A prova de cada finding aplicado, com `refused`, `unresolved` e a politica."""
    verdicts = {
        str(f.get("rule_id"))
        for f in union_verdicts
        if str(f.get("rule_id")).startswith(VEREDICTOS)
    }
    funcval_analyzed = any(f.get("kind") == "funcval.analyzed" for f in union_facts)
    run_delta, furos = _bench_da_uniao(union_facts)
    shared = len(applied_findings) > 1
    ids_por_modulo: dict[str, list[str]] = {}
    for fato in after_facts:
        modulo = emitted_by.get(str(fato.get("kind")), "")
        if modulo:
            ids_por_modulo.setdefault(modulo, []).append(str(fato.get("id")))
    resultados: list[dict[str, Any]] = []
    for finding in applied_findings:
        rule_id = str(finding.get("rule_id"))
        chave = stable_key(finding.get("subject") or {}, policy["stable_keys"])
        lidos = kinds_in_when((rules_by_id.get(rule_id) or {}).get("when"))
        evidencia = [str(f.get("id")) for f in after_facts if f.get("kind") in lidos]
        obrigacoes = [
            resolve(rule_id, chave, after_findings, after_skipped, policy["stable_keys"],
                    emitted_by, evidencia, ids_por_modulo),
            *_obrigacoes_de_eixo(finding, policy, verdicts, funcval_analyzed, run_delta, furos,
                                 shared),
        ]
        contagem = Counter(o["outcome"] for o in obrigacoes)
        resultados.append(
            {
                "rule_id": rule_id,
                "subject": dict(finding.get("subject") or {}),
                "stable_key": chave,
                "obligations": obrigacoes,
                "summary": {desfecho: contagem.get(desfecho, 0) for desfecho in OUTCOMES},
            }
        )
    return {
        "results": resultados,
        "applied_count": len(applied_findings),
        "attribution": "shared" if shared else "single",
        "refused": [dict(item) for item in REFUSED],
        "unresolved": [dict(item) for item in unresolved],
        "policy": {
            "policy_version": policy["policy_version"],
            "delta_sign_convention": dict(policy["delta_sign_convention"]),
        },
    }
