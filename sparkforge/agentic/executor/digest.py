"""O plano de aplicacao, calculado e nao gravado.

`plan_digest` monta o bloco que o `judge` publica: ordem, restricoes de
sequenciamento, contradicoes, objecoes e lacunas, mais o lastro por achado.

Ele NAO cria entidade e NAO toca o disco. `sparkforge_judge` e `READ_ONLY` e
continua sendo -- faze-lo gravar mudaria a cadeia de autorizacao de uma tool que
muitas skills chamam, e faria um verbo de leitura escrever no repositorio do
operador. O registro auditavel (blackboard, ADR, decisoes, `DebatePlan`
completo) continua sendo `sparkforge arbitrate`.

`run.py` usa este modulo em vez de repetir a sequencia: se os dois montassem o
plano por conta propria, divergiriam, e o operador veria o `judge` afirmar uma
ordem e o `arbitrate` outra sobre o mesmo case.
"""

from __future__ import annotations

from typing import Any

from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import standing_for_finding
from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts
from sparkforge.agentic.executor.ordering import order_actions
from sparkforge.agentic.executor.unknowns import unknowns_from

_NOTA = "calculado, nao gravado. O registro auditavel e `sparkforge arbitrate`."


def plan_digest(
    findings: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    runtime: dict[str, Any],
    authority_map: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Devolve `(bloco, lastro_por_rule_id)`.

    `bloco["scope"]` nomeia o conjunto e a contagem de proposito: a ordem e
    propriedade do CASO, e um consumidor que recebeu uma pagina leria a ordem
    como completa se nada dissesse o contrario.

    Chave ausente e pior que lista vazia: forma estavel e o que permite ao
    consumidor confiar na chave em vez de testar se ela existe. Por isso o bloco
    sai com as mesmas nove chaves sempre, mesmo num case sem achado nenhum.
    """
    mapa = authority_map if authority_map is not None else load_authority_map()
    findings = list(findings or [])
    facts = list(facts or [])

    ids_presentes = {
        str(f.get("id")) for f in facts if isinstance(f, dict) and f.get("id")
    }

    acao_por_regra = {
        str(f.get("rule_id")): (f.get("action") or {})
        for f in findings
        if f.get("rule_id")
    }

    ordem, restricoes, ordem_unresolved = order_actions(findings)

    contradicoes = [
        {
            "rules": [a, b],
            "target": str(acao_por_regra.get(a, {}).get("target") or ""),
            "directions": [
                str(acao_por_regra.get(a, {}).get("direction") or ""),
                str(acao_por_regra.get(b, {}).get("direction") or ""),
            ],
        }
        for a, b in direct_conflicts(findings)
    ]

    objecoes = [
        {"rule": rule_id, "blocked_by_kind": kind, "fact_id": fact_id}
        for rule_id, kind, fact_id in conditional_conflicts(findings, facts)
    ]

    lacunas = [
        {"question": u.question, "evidence_needed": list(u.evidence_needed)}
        for u in unknowns_from(findings, facts)
    ]

    lastro = {
        str(f["rule_id"]): standing_for_finding(f, ids_presentes, mapa, runtime)
        for f in findings
        if f.get("rule_id")
    }

    bloco = {
        "scope": f"todos os {len(findings)} achados deste case, nao a pagina",
        "order": ordem,
        "order_unresolved": ordem_unresolved,
        "constraints": restricoes,
        "contradictions": contradicoes,
        "objections": objecoes,
        "unresolved": lacunas,
        "persisted": False,
        "note": _NOTA,
    }
    return bloco, lastro
