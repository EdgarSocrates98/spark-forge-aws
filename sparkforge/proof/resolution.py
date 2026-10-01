"""A obrigacao de resolucao: a regra que recomendou deixou de disparar?

`requires_facts` no `skipped` quer dizer "o kind que a regra le nao existe no
depois" -- e ha dois jeitos de ele nao existir, com desfechos opostos:

- o extrator que emite aquele kind RODOU no depois (produziu algum fact do mesmo
  modulo) e simplesmente nao encontrou o padrao: a correcao tirou o `collect()`,
  e `pyspark.driver_collect` sumiu. A ausencia e evidencia -> `not_refuted`;
- o extrator NAO rodou: faltou artefato -> `unproven`, com os kinds que faltam e
  o modulo que os emitiria.

Medido em 2026-09-12 sobre `collect_unbounded` corrigido: `SF-PY-002` declara
`requires_facts: [pyspark.driver_collect]`, e o depois tem
`pyspark.module_analyzed` do mesmo extrator. Sem esta distincao, a correcao
bem-sucedida sairia `unproven`.

`runtime_scope` e `blocked_on` sao silencios de outra natureza -- a regra nao se
aplica a este runtime, ou a capacidade que ela exige ainda nao existe. Nenhum e
resolucao, e nenhum se conserta coletando artefato: saem `inconclusive`.

A comparacao de disparo e pela chave estavel (`keys.stable_key`), nunca pelo
subject inteiro.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.proof.keys import stable_key

_SILENCIO_SEM_ARTEFATO = "requires_facts"
_SILENCIO_DE_ESCOPO = {
    "runtime_scope": "regra_fora_do_escopo_no_depois",
    "blocked_on": "regra_bloqueada",
}


def _sem_o_kind(
    obrigacao: dict[str, Any],
    faltam: list[str],
    emitted_by: Mapping[str, str],
    after_ids_by_module: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Kind ausente: padrao sumido (extrator rodou) ou artefato faltando."""
    modulos = {kind: emitted_by.get(kind, "") for kind in faltam}
    sem_extrator = sorted(k for k, m in modulos.items() if not m or not after_ids_by_module.get(m))
    if sem_extrator:
        return {
            **obrigacao,
            "outcome": "unproven",
            "reason": "regra_muda_no_depois",
            "missing_kinds": sem_extrator,
            "unlock": {kind: modulos[kind] for kind in sem_extrator},
        }
    evidencia = sorted({i for m in set(modulos.values()) for i in after_ids_by_module[m]})
    return {
        **obrigacao,
        "outcome": "not_refuted",
        "reason": "padrao_ausente_com_extrator_rodado",
        "absent_kinds": faltam,
        "evidence": evidencia,
    }


def resolve(
    rule_id: str,
    key: Mapping[str, Any] | None,
    after_findings: Sequence[Mapping[str, Any]],
    after_skipped: Sequence[Mapping[str, Any]],
    stable_keys: Mapping[str, list[str]],
    emitted_by: Mapping[str, str],
    after_evidence: Sequence[str],
    after_ids_by_module: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """O desfecho da resolucao de um finding aplicado."""
    obrigacao: dict[str, Any] = {"kind": "resolution", "rule_id": rule_id}
    if key is None:
        return {**obrigacao, "outcome": "inconclusive", "reason": "subject_sem_chave_estavel"}
    for item in after_skipped:
        if item.get("rule_id") != rule_id:
            continue
        razao = str(item.get("reason") or "")
        if razao == _SILENCIO_SEM_ARTEFATO:
            faltam = sorted(str(kind) for kind in item.get("missing") or [])
            return _sem_o_kind(obrigacao, faltam, emitted_by, after_ids_by_module or {})
        return {
            **obrigacao,
            "outcome": "inconclusive",
            "reason": _SILENCIO_DE_ESCOPO.get(razao, "regra_nao_avaliada_no_depois"),
        }
    for finding in after_findings:
        if finding.get("rule_id") != rule_id:
            continue
        if stable_key(finding.get("subject") or {}, stable_keys) == dict(key):
            return {
                **obrigacao,
                "outcome": "refuted",
                "reason": "regra_ainda_dispara",
                "evidence": sorted(str(i) for i in finding.get("evidence") or []),
            }
    return {
        **obrigacao,
        "outcome": "not_refuted",
        "reason": "regra_avaliada_e_nao_disparou",
        "evidence": sorted(str(i) for i in after_evidence),
    }
