"""Remocao dos derivados e comparacao dos dois lados.

Os dois lados passam pelo MESMO pipeline: tirar os kinds que `fusion`,
`lakeformation` e `timeout_diagnosis` derivam e rederiva-los. Assim a diferenca
so pode vir do `--set`, e nunca de uma rederivacao que so um lado sofreu.

A comparacao e por `(rule_id, chave estavel do subject)`. Alterar
`measures.value` muda o `Fact.id`, e a chave estavel ignora o que muda sem
significar nada; subject sem chave declarada compara inteiro -- no simulate os
dois lados tem o mesmo subject, porque o `--set` nunca o toca.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.facts import fusion, lakeformation, timeout_diagnosis
from sparkforge.findings.models import Fact
from sparkforge.proof.keys import stable_key

DERIVED_KINDS = frozenset(
    fusion.EMITTED_KINDS | lakeformation.EMITTED_KINDS | timeout_diagnosis.EMITTED_KINDS
)
AVALIADA = "evaluated"


def strip_derived(facts: Sequence[Fact]) -> list[Fact]:
    return [f for f in facts if f.kind not in DERIVED_KINDS]


def _chave(finding: Mapping[str, Any], stable_keys: Mapping[str, list[str]]) -> tuple[str, str]:
    subject = finding.get("subject") or {}
    estavel = stable_key(subject, stable_keys)
    return str(finding.get("rule_id")), json.dumps(estavel or subject, sort_keys=True)


def _por_chave(
    findings: Sequence[Mapping[str, Any]], stable_keys: Mapping[str, list[str]]
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {_chave(f, stable_keys): f for f in findings}


def _pulos(skipped: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {str(s.get("rule_id")): str(s.get("reason") or "") for s in skipped}


def diff(
    before_findings: Sequence[Mapping[str, Any]],
    after_findings: Sequence[Mapping[str, Any]],
    before_skipped: Sequence[Mapping[str, Any]],
    after_skipped: Sequence[Mapping[str, Any]],
    stable_keys: Mapping[str, list[str]],
) -> dict[str, Any]:
    antes = _por_chave(before_findings, stable_keys)
    depois = _por_chave(after_findings, stable_keys)
    sumiram = sorted(set(antes) - set(depois))
    surgiram = sorted(set(depois) - set(antes))
    pulos_antes, pulos_depois = _pulos(before_skipped), _pulos(after_skipped)
    mudaram = sorted(
        r for r in set(pulos_antes) | set(pulos_depois)
        if pulos_antes.get(r, AVALIADA) != pulos_depois.get(r, AVALIADA)
    )
    return {
        "disappeared": [
            {"rule_id": k[0], "subject": dict(antes[k].get("subject") or {})} for k in sumiram
        ],
        "appeared": [
            {"rule_id": k[0], "subject": dict(depois[k].get("subject") or {})} for k in surgiram
        ],
        "persisted_count": len(set(antes) & set(depois)),
        "skipped_delta": [
            {"rule_id": r, "before": pulos_antes.get(r, AVALIADA),
             "after": pulos_depois.get(r, AVALIADA)}
            for r in mudaram
        ],
    }
