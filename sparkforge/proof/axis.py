"""A obrigacao de um eixo de `action.moves`.

`funcval`: os veredictos `SF-FVAL-001..004` refutam; `SF-FVAL-005` (validacao
parcial) deixa inconclusivo; sem nenhum, a obrigacao nao foi refutada -- e o
limite vai escrito, porque os quatro proxies passam mesmo com duas linhas
trocando valores entre si.

`bench`, na ordem da Decision 3 do DESIGN, e o primeiro que casa decide:
stages nao casados; volumes de entrada diferentes (no eixo de leitura, volume e
leitura indistinguiveis); event log ausente num lado; medida sem delta; varias
mudancas aplicadas; regra que julga o eixo; sinal do delta pela convencao
declarada.

`none`: `unproven`, com o `unlock` da politica.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

FUNCVAL_REFUTAM = ("SF-FVAL-001", "SF-FVAL-002", "SF-FVAL-003", "SF-FVAL-004")
FUNCVAL_PARCIAL = "SF-FVAL-005"
BENCH_NAO_CASOU = "SF-BENCH-004"
BENCH_VOLUME = "SF-BENCH-001"
BENCH_SEM_LOG = "missing_log_analyzed"

FUNCVAL_UNLOCK = (
    "sparkforge funcval plan ... --out <plano> e sparkforge funcval compare "
    "--plan <plano> --before <resultado-antes> --after <resultado-depois>"
)
BENCH_UNLOCK = (
    "sparkforge benchmark --before <facts-de-event-log-antes> --after "
    "<facts-de-event-log-depois>"
)
FUNCVAL_LIMITE = "nenhum dos quatro proxies detectou divergencia; isso nao prova identidade"


def funcval_outcome(axis: str, verdicts: set[str], analyzed: bool) -> dict[str, Any]:
    base: dict[str, Any] = {"kind": "axis", "axis": axis, "source": "funcval"}
    if not analyzed:
        return {**base, "outcome": "unproven", "reason": "sem_funcval", "unlock": FUNCVAL_UNLOCK}
    refutam = sorted(verdicts.intersection(FUNCVAL_REFUTAM))
    if refutam:
        return {**base, "outcome": "refuted", "verdicts": refutam}
    if FUNCVAL_PARCIAL in verdicts:
        return {**base, "outcome": "inconclusive", "reason": "validacao_parcial",
                "verdicts": [FUNCVAL_PARCIAL]}
    return {**base, "outcome": "not_refuted", "limit": FUNCVAL_LIMITE,
            "verdicts_checked": [*FUNCVAL_REFUTAM, FUNCVAL_PARCIAL]}


def bench_outcome(
    axis: str,
    spec: Mapping[str, Any],
    verdicts: set[str],
    run_delta: Mapping[str, Any] | None,
    unresolved: Sequence[Mapping[str, Any]],
    shared: bool,
) -> dict[str, Any]:
    base: dict[str, Any] = {"kind": "axis", "axis": axis, "source": "bench",
                            "measure": spec["measure"]}
    if spec.get("proxy"):
        base["proxy"] = spec["proxy"]
    if run_delta is None:
        return {**base, "outcome": "unproven", "reason": "sem_benchmark", "unlock": BENCH_UNLOCK}
    if BENCH_NAO_CASOU in verdicts:
        return {**base, "outcome": "inconclusive", "reason": "stages_nao_casados",
                "verdicts": [BENCH_NAO_CASOU]}
    if BENCH_VOLUME in verdicts:
        confundido = BENCH_VOLUME in (spec.get("confounded_by") or [])
        razao = (
            "volume_ou_leitura_indistinguiveis" if confundido else "volumes_de_entrada_diferentes"
        )
        return {**base, "outcome": "inconclusive", "reason": razao, "verdicts": [BENCH_VOLUME]}
    if any(item.get("reason") == BENCH_SEM_LOG for item in unresolved):
        return {**base, "outcome": "inconclusive", "reason": "event_log_ausente_num_lado"}
    furo = next((i for i in unresolved if i.get("measure") == spec["measure"]), None)
    pct = run_delta.get(f"{spec['measure']}_delta_pct")
    if furo is not None or pct is None:
        razao = str(furo.get("reason")) if furo is not None else "delta_sem_base"
        return {**base, "outcome": "inconclusive", "reason": razao}
    base["delta_pct"] = pct
    if shared:
        return {**base, "outcome": "inconclusive", "reason": "attribution_shared"}
    refutam = sorted(verdicts.intersection(spec.get("refuted_by") or []))
    if refutam:
        return {**base, "outcome": "refuted", "verdicts": refutam}
    if pct >= 0:
        return {**base, "outcome": "refuted", "reason": "delta_contra_improves_when",
                "convention": "delta_sign_convention"}
    return {**base, "outcome": "not_refuted", "convention": "delta_sign_convention"}


def none_outcome(axis: str, spec: Mapping[str, Any] | None) -> dict[str, Any]:
    base: dict[str, Any] = {"kind": "axis", "axis": axis, "source": "none", "outcome": "unproven"}
    if spec is None:
        return {**base, "reason": "eixo_sem_politica",
                "unlock": "declarar o eixo em rules/catalog/proof_axes.yaml"}
    return {**base, "reason": "sem_comparador", "unlock": str(spec.get("unlock") or "").strip()}
