"""Planos de contexto por role dos cinco executores.

Onde isso morde: `ContextGateway.start` resolve `role`/`role_plan` do
`GatewayRequest` contra este registro e aplica `plan.allows()` item a item --
a negacao vira `unresolved` nomeado, nunca sumico silencioso.

Como as listas foram derivadas: do `## Nao faz` de cada `agents/executors/*.md`.
O contrato negativo do executor diz o que ele NAO produz; o `allowed_context`
daqui diz o que ele PRECISA LER. Ex.: o juiz aplica regra sobre fato -- le
`fact`/`rule`, e `tool_output` cru nao entra porque julgar texto de tool sem
extracao deterministica seria pular a fronteira que o `## Nao faz` dele protege.

`trust_floor=UNKNOWN` em todos, DE PROPOSITO NESTA V1: produtores de `items`
ainda nao etiquetam `trust`, e um floor mais alto negaria tudo que chega sem
rotulo (item sem `trust` resolve `UNKNOWN`, rank 0). O mecanismo e real -- o
teste prova o floor negando -- mas o aperto espera os produtores etiquetarem.
Subir floor antes disso nao endurece seguranca: torna o gateway inutil.
"""

from __future__ import annotations

from sparkforge.agentic.trust import RoleContextPlan, TrustLabel

ROLE_PLANS: dict[str, RoleContextPlan] = {
    # Inventario enumera e le runtime: artefato, codigo e conhecimento de
    # versao. Nao precisa de fact/finding -- nao extrai nem julga.
    "sf-inventory": RoleContextPlan(
        role="sf-inventory",
        allowed_context=("artifact", "code", "knowledge", "context", "unresolved"),
        context_share=0.6,
        trust_floor=TrustLabel.UNKNOWN,
    ),
    # Extrator le artefato e codigo para PRODUZIR fact; nao consome fact nem
    # finding de outros -- isso e input do juiz e do verificador.
    "sf-extractor": RoleContextPlan(
        role="sf-extractor",
        allowed_context=("artifact", "code", "knowledge", "context", "unresolved"),
        required_context=("artifact",),
        context_share=0.8,
        trust_floor=TrustLabel.UNKNOWN,
    ),
    # Juiz cruza fact com rule para PRODUZIR finding. Sem fact nao ha julgamento
    # (fact e `required`); sem rule o veredito sai sem rule_id -- invalido por
    # construcao, entao rule tambem e exigido.
    "sf-judge": RoleContextPlan(
        role="sf-judge",
        allowed_context=("fact", "rule", "knowledge", "unresolved"),
        required_context=("fact", "rule"),
        context_share=0.7,
        trust_floor=TrustLabel.UNKNOWN,
    ),
    # Verificador tenta refutar finding contra fact/evidence. Recomendacao nao
    # e input dele -- quem conserta nao verifica e quem verifica nao conserta.
    "sf-verifier": RoleContextPlan(
        role="sf-verifier",
        allowed_context=("finding", "fact", "evidence", "unresolved", "risk"),
        required_context=("finding",),
        context_share=0.7,
        trust_floor=TrustLabel.UNKNOWN,
    ),
    # Sintetizador compoe a resposta final: le o que sobreviveu (finding, fact,
    # risk, unresolved) e memoria/knowledge para redigir -- sem artefato cru,
    # porque a esta altura tudo ja passou por extracao deterministica.
    "sf-synthesizer": RoleContextPlan(
        role="sf-synthesizer",
        allowed_context=("finding", "fact", "risk", "unresolved", "knowledge", "memory"),
        required_context=("finding",),
        context_share=1.0,
        trust_floor=TrustLabel.UNKNOWN,
    ),
}


def role_plan(name: str) -> RoleContextPlan | None:
    """O plano declarado da role, ou `None` quando a role nao tem plano.

    `None` e resposta honesta para o gateway transformar em fail-closed:
    role sem plano nao ganha contexto de graca.
    """
    return ROLE_PLANS.get(name)


__all__ = ["ROLE_PLANS", "role_plan"]
