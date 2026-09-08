"""`DebatePlan` -- o que sai quando a arbitragem nao fecha (secao 6 do spec).

Este e o **limite declarado** da entrega, e o desenho inteiro depende dele estar
honesto. Quando a contradicao nao resolve deterministicamente -- `disputed` com
autoridade empatada, ou `recommendation` em `escalate`/`experiment` -- o
executor nao inventa vencedor. Ele emite quem debateria, com o que, sob que
teto, e **para**.

## De onde vem o participante

`rules/catalog/routing.yaml` ja casa area de finding com coordenador: as regras
`AGENT-*` tem `when.{all,any}[].findings_area` de um lado e `recommended_agent`
do outro. A area sai do proprio `rule_id` (`SF-GLUE-001` -> `SF-GLUE`), e o mapa
cobre 61 areas. A derivacao E possivel, entao ela e feita -- e a regra cuja area
o catalogo nao roteia sai em `participants_unresolved`, no proprio plano.

Escrever a limitacao em comentario de codigo foi descartado pelo motivo obvio:
quem le o plano nao le o codigo. Lacuna que nao viaja com a saida e lacuna que
ninguem conserta.

O arquivo e avaliado em ordem e o primeiro match vence (o cabecalho do proprio
`routing.yaml` diz isso), entao area com mais de uma regra `AGENT-*` fica com o
agente da primeira. Escolher outro criterio -- o mais especifico, o ultimo --
divergiria do que `next_step` faz com o mesmo arquivo, e duas leituras do mesmo
dado dando respostas diferentes e pior que uma leitura imperfeita.

## Por que `rounds` sai `unresolved` mesmo com budget declarado

O bloco `budget:` do `case.yaml` aceita sete chaves, e nenhuma delas e rodada:
`max_debates` conta DEBATES, nao rodadas dentro de um. Rodada so existe em
`DebateBudget.max_rounds`, que e default de codigo. Copia-lo para o plano seria
reencenar num campo novo o defeito que a auditoria de 2026-09-03 corrigiu em
`sparkforge budget show` -- ele imprimia `CaseBudget()` de fabrica como se fosse
o estado do case. O default do codigo e template; template nao vira medida por
ser impresso ao lado de dados medidos.

## Por que o budget invalido nao derruba a emissao

`case_budget_from_case` levanta `ValueError` nomeando a chave errada, e e o
contrato certo para `budget show`, que existe para VALIDAR. Aqui o produto e o
plano de debate; matar o plano por causa do bloco de budget seria instrumentacao
quebrando o produto (regra 27). A mensagem do erro viaja dentro de
`budget.reason`, entao nada se perde.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from sparkforge.agentic.budget import CASE_BUDGET_KEY, case_budget_from_case

# `SF-STEP-FUNCTIONS-004` -> `SF-STEP-FUNCTIONS`. O ordinal e o ultimo grupo de
# digitos depois de um hifen, e so ele. Separar por hifen e jogar fora o ultimo
# pedaco daria o mesmo resultado nos ids de hoje e quebraria calado no dia em que
# uma area tiver sufixo nao numerico.
_ORDINAL = re.compile(r"^(?P<area>.+)-\d+$")

_MOTIVO_SEM_EXECUTOR = (
    "este pacote nao tem executor de debate: ele emite o plano e para. O que "
    "destravaria e um `AgentRuntime` concreto, implementado FORA deste pacote "
    "pelo host -- `sparkforge/` nao chama provider nenhum (regra 23)"
)

_MOTIVO_SEM_RODADA = (
    "o bloco `budget:` do case.yaml nao tem campo de rodadas -- `max_debates` "
    "conta debates, nao rodadas dentro de um. Rodada so existe em "
    "`DebateBudget.max_rounds`, que e default de codigo (template), nunca "
    "estado do case"
)

_cache_de_rota: dict[str, str] | None = None


def _routing_path() -> Path:
    """Caminho default de `rules/catalog/routing.yaml`.

    Mesma resolucao de `ordering._action_kinds_path`: `parents[3]` porque este
    arquivo esta em `sparkforge/agentic/executor/`.
    """
    return Path(__file__).resolve().parents[3] / "rules" / "catalog" / "routing.yaml"


def load_routing_agents(path: Path | None = None) -> dict[str, str]:
    """Mapa `findings_area -> recommended_agent`, lido de `routing.yaml`.

    Args:
        path: alternativa ao catalogo do repositorio. Existe para o teste poder
            fixar o mapa, como `ordering.load_measure_axes` faz com os eixos.

    Returns:
        Uma area por chave, com o agente da PRIMEIRA regra que a nomeia -- o
        arquivo e avaliado em ordem e o primeiro match vence.

    Regras `AGENT-*` que casam por `case.scope.entrypoints` em vez de
    `findings_area` nao entram: elas roteiam por estado do case, e um `rule_id`
    nao carrega estado de case. Deriva-las daqui produziria participante que a
    regra em disputa nao sustenta.
    """
    alvo = Path(path) if path is not None else _routing_path()
    documento = yaml.safe_load(alvo.read_text(encoding="utf-8-sig")) or {}

    mapa: dict[str, str] = {}
    for regra in documento.get("rules") or []:
        if not isinstance(regra, dict):
            continue
        agente = str(regra.get("recommended_agent") or "").strip()
        if not agente:
            continue
        for condicoes in (regra.get("when") or {}).values():
            for condicao in condicoes if isinstance(condicoes, list) else []:
                if not isinstance(condicao, dict):
                    continue
                area = str(condicao.get("findings_area") or "").strip()
                if area:
                    mapa.setdefault(area, agente)
    return mapa


def agent_for_area(area: str, mapa: dict[str, str] | None = None) -> str | None:
    """O coordenador que `routing.yaml` declara para a area, ou `None`.

    O mapa e memorizado num modulo-level cache porque `debate_plan` o consulta
    uma vez por regra e o arquivo tem 1200 linhas. O cache e so quando ninguem
    passa `mapa` -- caller que traz o proprio catalogo nunca o envenena.
    """
    global _cache_de_rota
    if mapa is None:
        if _cache_de_rota is None:
            _cache_de_rota = load_routing_agents()
        mapa = _cache_de_rota
    return mapa.get(area)


def area_of(rule_id: str) -> str:
    """A area de um `rule_id`, sem o ordinal. `SF-GLUE-001` -> `SF-GLUE`.

    Id sem ordinal devolve `""` em vez do id inteiro. Aceita-lo como area faria
    `SF-GLUE` casar no mapa e produzir um participante a partir de um id
    malformado -- deriva silenciosa e o que este projeto chama de fake.
    """
    casou = _ORDINAL.match(str(rule_id or "").strip())
    return casou.group("area") if casou else ""


def debate_plan(
    rule_ids: list[str], fact_ids_por_regra: dict[str, list[str]], budget: dict | None
) -> dict:
    """O plano de debate, emitido e nao executado.

    Args:
        rule_ids: as regras em disputa, na ordem em que a arbitragem as viu.
        fact_ids_por_regra: os `fact.id` que ancoram cada regra. Regra sem
            entrada recebe contexto vazio -- e o que o case tem, e inventar
            fact para preencher seria pior que a lista curta.
        budget: o bloco `budget:` do `case.yaml`, ou `None`. **Nunca** o default
            do codigo: sem bloco o plano sai `unresolved` nomeando a lacuna.

    Returns:
        Um dicionario serializavel com `participants`,
        `participants_unresolved`, `budget`, `rounds`, `stop_criteria`,
        `executed` e `unresolved`.
    """
    ordem_de_agentes: list[str] = []
    por_agente: dict[str, dict[str, list[str]]] = {}
    sem_agente: list[dict[str, str]] = []

    for bruto in rule_ids if isinstance(rule_ids, (list, tuple)) else []:
        rule_id = str(bruto or "").strip()
        if not rule_id:
            continue
        area = area_of(rule_id)
        agente = agent_for_area(area) if area else None
        if agente is None:
            sem_agente.append(
                {
                    "rule_id": rule_id,
                    "area": area,
                    "reason": (
                        "routing.yaml nao declara `recommended_agent` para esta "
                        "area por `findings_area`; sem isso o participante seria "
                        "escolhido por julgamento, e nao por dado"
                    ),
                }
            )
            continue

        if agente not in por_agente:
            por_agente[agente] = {"areas": [], "rules": [], "context_fact_ids": []}
            ordem_de_agentes.append(agente)
        registro = por_agente[agente]
        if area not in registro["areas"]:
            registro["areas"].append(area)
        if rule_id not in registro["rules"]:
            registro["rules"].append(rule_id)
        for fact_id in _facts_da_regra(fact_ids_por_regra, rule_id):
            if fact_id not in registro["context_fact_ids"]:
                registro["context_fact_ids"].append(fact_id)

    limites = _limites(budget)
    parada = _criterio_de_parada(limites)

    return {
        "kind": "debate.plan",
        "participants": [{"agent": nome, **por_agente[nome]} for nome in ordem_de_agentes],
        "participants_unresolved": sem_agente,
        "budget": limites,
        "rounds": {"status": "unresolved", "reason": _MOTIVO_SEM_RODADA},
        "stop_criteria": parada,
        "stop_criteria_status": "declared" if parada else "unresolved",
        "executed": False,
        "unresolved": {
            "reason": "debate.unresolved",
            "unblocked_by": _MOTIVO_SEM_EXECUTOR,
        },
    }


def _facts_da_regra(
    fact_ids_por_regra: dict[str, list[str]] | None, rule_id: str
) -> list[str]:
    """Os `fact.id` daquela regra, deduplicados na ordem de aparicao."""
    if not isinstance(fact_ids_por_regra, dict):
        return []
    brutos = fact_ids_por_regra.get(rule_id) or []
    if not isinstance(brutos, (list, tuple)):
        return []
    vistos: list[str] = []
    for bruto in brutos:
        fact_id = str(bruto or "").strip()
        if fact_id and fact_id not in vistos:
            vistos.append(fact_id)
    return vistos


def _limites(budget: dict | None) -> dict[str, Any]:
    """Os tetos DECLARADOS, ou `unresolved` nomeando a lacuna.

    `budget: {}` conta como ausente. Um mapa vazio nao declara teto nenhum, e
    devolve-lo como "declarado, sem limites" diria que o case autorizou debate
    infinito -- que e o oposto do que um bloco vazio significa.
    """
    if not budget:
        return {
            "status": "unresolved",
            "reason": (
                f"o case.yaml nao declara o bloco `{CASE_BUDGET_KEY}:`. Sem teto "
                f"declarado nao ha budget deste case, e o default do codigo e "
                f"template, nao medida -- veja `sparkforge budget show "
                f"--template`"
            ),
        }

    try:
        declarado = case_budget_from_case({CASE_BUDGET_KEY: budget})
    except ValueError as exc:
        return {"status": "unresolved", "reason": str(exc)}

    if declarado is None:  # pragma: no cover -- `budget` truthy garante o bloco
        return {"status": "unresolved", "reason": "bloco ausente"}

    # So o que o case DECLAROU viaja. `to_dict` traz os sete `max_*` -- inclusive
    # os que o bloco nao nomeou, preenchidos pelo default do dataclass -- e
    # emiti-los todos seria exatamente o vazamento de fabrica que este modulo
    # existe para impedir.
    limites: dict[str, Any] = {"status": "declared"}
    completo = declarado.to_dict()
    for chave in sorted(budget):
        if chave in completo:
            limites[chave] = completo[chave]
    return limites


def _criterio_de_parada(limites: dict[str, Any]) -> list[str]:
    """O criterio de parada, derivado dos tetos declarados.

    Sem budget a lista sai VAZIA, e nao com uma frase generica. "Para quando
    convergir" nao e criterio: ninguem consegue conferir se aconteceu. A lacuna
    sai em `stop_criteria_status`, do lado.
    """
    if limites.get("status") != "declared":
        return []
    return [
        f"{chave} = {valor}"
        for chave, valor in limites.items()
        if chave.startswith("max_")
    ]
