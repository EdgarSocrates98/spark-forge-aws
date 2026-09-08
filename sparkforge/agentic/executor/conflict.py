"""Os dois modos de contradicao da secao 4 do spec, sobre o bloco `action:`.

- **Direta** -- duas acoes com o mesmo `target` e direcao oposta.
- **Condicional** -- o `requires_absent` de uma acao esta MEDIDO entre os facts
  do case.

Alvos diferentes nao sao contradicao. Sao ordem, e caem em
`sparkforge.agentic.executor.ordering`.

## Por que a contradicao direta NAO filtra por eixo de medida

Isto e decisao medida, e o registro importa porque a alternativa parecia melhor.

Filtrar o par por eixo compartilhado de `nature: measure` foi tentado. Ele
apagava o unico caso REAL do catalogo junto com o falso positivo que se queria
matar:

- o falso positivo era `SF-PLAN-003` (acrescentar a equi-condicao que falta) x
  `SF-PY-009` (remover hint de broadcast), com o mesmo `target: pyspark.join`.
  O defeito nunca foi o eixo: era o `target` GROSSO DEMAIS, cobrindo a condicao
  do join e o hint do join como se fossem a mesma coisa. A correcao foi refinar
  os targets (`pyspark.join.condition`, `pyspark.join.hint`), que e onde o
  defeito morava;
- o caso real e `SF-GRAPH-005` x `SF-LF-001`, e o unico eixo que os dois
  compartilham -- `dependency.delivered_artifacts` -- e `nature: risk`. Um
  filtro por eixo de medida o apagaria tambem.

Filtrar o criterio para compensar target impreciso teria escondido o problema em
vez de corrigi-lo. `nature` continua certo -- so que para a restricao de
sequenciamento de `ordering.py`, que precisa mesmo de grandeza comparavel.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# As duas oposicoes declaradas. `replace` (46 das 112) e `investigate` (23) nao
# aparecem: nenhuma das duas tem contraria.
#
# `investigate` merece a nota, porque a tentacao e trata-lo como oposto de
# mudanca. Medir e mudar no mesmo alvo nao se contradizem -- eles se ORDENAM, e
# essa e literalmente a primeira restricao derivada da secao 5.4.
_OPOSTAS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"increase", "decrease"}),
        frozenset({"add", "remove"}),
    }
)


def direct_conflicts(findings: list[dict]) -> list[tuple[str, str]]:
    """Pares de `rule_id` cujas acoes tocam o mesmo `target` em direcoes opostas.

    Args:
        findings: findings julgados. So `rule_id` e `action` sao lidos; finding
            sem bloco `action` nao participa -- ele nao propoe mudanca nenhuma,
            e nao ha o que contradizer.

    Returns:
        Lista de tuplas `(rule_id_menor, rule_id_maior)`, sem repeticao e
        ordenada. O par sai ordenado dentro e fora porque o mesmo conflito visto
        de dois lados tem que ser UM: `sparkforge/agentic/evidence.py::
        detect_conflicts` prometia isso na docstring e nao ordenava nada, e a
        consequencia medida foi o mesmo conflito saindo como duas tuplas
        diferentes conforme o hash -- qualquer deduplicacao rio abaixo contaria
        dois (secao 12.7 do spec).

    A mesma regra nao contradiz a si mesma. Duas ocorrencias da mesma regra sobre
    sujeitos diferentes sao dois findings e uma acao so: ela propoe a mesma coisa
    nos dois, e `(SF-A, SF-A)` seria uma contradicao inventada pelo agrupamento.
    """
    por_alvo: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for finding in findings or []:
        acao = _acao(finding)
        if not acao:
            continue
        alvo = str(acao.get("target") or "").strip()
        direcao = str(acao.get("direction") or "").strip()
        rule_id = str(finding.get("rule_id") or "").strip()
        if not alvo or not direcao or not rule_id:
            continue
        por_alvo[alvo].append((rule_id, direcao))

    pares: set[tuple[str, str]] = set()
    for candidatos in por_alvo.values():
        for i, (regra_a, direcao_a) in enumerate(candidatos):
            for regra_b, direcao_b in candidatos[i + 1 :]:
                if regra_a == regra_b:
                    continue
                if frozenset({direcao_a, direcao_b}) in _OPOSTAS:
                    pares.add(tuple(sorted((regra_a, regra_b))))  # type: ignore[arg-type]

    return sorted(pares)


def conditional_conflicts(
    findings: list[dict], facts: list[dict]
) -> list[tuple[str, str, str]]:
    """Guardas `requires_absent` que estao MEDIDAS entre os facts do case.

    Args:
        findings: findings julgados, como em `direct_conflicts`.
        facts: facts do case. So `id` e `kind` sao lidos.

    Returns:
        Lista ordenada de `(rule_id, kind_proibido, fact_id)`.

    O `fact_id` entra porque a contradicao precisa apontar a MEDIDA, e nao so o
    nome do kind. A secao 4 exige os `fact.id` dos dois lados; devolver so o kind
    diria "o sintoma esta presente" sem dizer onde ele foi medido, e quem lesse o
    relatorio nao teria como conferir. Dois facts do mesmo kind sao duas medidas,
    e as duas saem.

    **Hoje isto devolve `[]` para todo case real, e esse e o estado correto.**
    As quatro guardas do catalogo (`emr.configuration.unapplied` x2,
    `emrc.pod_template.unresolved`, `env.unresolved`) sao KINDS DE RECUSA: dizem
    *nao deu para ler*, nunca *o problema esta presente* -- e a regra que guarda
    contra a recusa nao dispara quando a leitura falhou. Onze candidatas de
    sintoma foram medidas e recusadas nos sete lotes, sempre porque o kind sai
    sempre ou sai por motivos sem relacao (secao 12.5 do spec).

    Mecanismo sem caso e `unresolved` nomeado, nunca funcionalidade entregue: o
    que destravaria e um kind emitido so acima do limiar, ou um `requires_absent`
    que saiba cruzar por `attrs` alem do kind.
    """
    ids_por_kind: dict[str, list[str]] = defaultdict(list)
    for fact in facts or []:
        if not isinstance(fact, dict):
            continue
        kind = str(fact.get("kind") or "").strip()
        fact_id = str(fact.get("id") or "").strip()
        if kind and fact_id:
            ids_por_kind[kind].append(fact_id)

    achados: set[tuple[str, str, str]] = set()
    for finding in findings or []:
        acao = _acao(finding)
        if not acao:
            continue
        rule_id = str(finding.get("rule_id") or "").strip()
        if not rule_id:
            continue
        for bruto in acao.get("requires_absent") or []:
            kind = str(bruto).strip()
            for fact_id in ids_por_kind.get(kind, ()):
                achados.add((rule_id, kind, fact_id))

    return sorted(achados)


def _acao(finding: Any) -> dict[str, Any]:
    """O bloco `action` do finding, ou `{}` quando ele nao tem um.

    Devolver `{}` em vez de levantar e a mesma leitura de `authority.tier_for_url`
    para URL ilegivel: um finding sem `action` e um finding que nao propoe
    mudanca, e isso ja tem resposta -- ele nao participa. Derrubar o pacote
    inteiro por causa de um finding sem bloco seria a regra 27 ao contrario.
    """
    if not isinstance(finding, dict):
        return {}
    acao = finding.get("action")
    return acao if isinstance(acao, dict) and acao else {}
