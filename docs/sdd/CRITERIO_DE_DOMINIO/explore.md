---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Criterio escrito e gate nos tres niveis. Um teste novo trava: (1) o catalogo commitado nao tem regra executable: false, e toda area tem ao menos uma regra executavel cujos kinds exigidos saem de extrator (sem blocked_on em todas); (2) todo coordenador de agents/ declara ao menos uma area com regra executavel; (3) todo coordenador tem ao menos uma rota que dispara por finding ou fact, nao so por __agentic_*__. O criterio vira secao em docs/gates-por-mudanca.md, com ponteiro de uma linha no CLAUDE.md e no AGENTS.md. Os sete sf-* que hoje so tem rota __agentic_*__ sao decididos nesta feature."
    tradeoffs:
      - "fecha a porta que o SF_STUBS abriu na mao: area oca ou coordenador sem dominio volta a cair num teste, nao numa revisao"
      - "obriga a decidir os sete sf-* agora (apagar, ou dar rota real); seis deles duplicam areas de coordenadores classicos"
      - "o criterio mora em documento que ja e lido por quem acrescenta area (gates-por-mudanca), sem regra numerada nova no CLAUDE.md"
  - id: B
    summary: "A sem o nivel (3): o gate trava area e coordenador, e a rota __agentic_*__ continua valendo como modo declarado pelo operador no case.yaml. Os sete sf-* ficam."
    tradeoffs:
      - "menor, e nao apaga nada"
      - "mantem sete coordenadores que o roteador nunca escolhe por conta propria, seis deles com as mesmas areas de outro coordenador"
      - "o __agentic_*__ e opt-in do operador, e isso e defensavel como modo; mas nenhum documento o ensina hoje"
  - id: C
    summary: "So o criterio escrito, sem gate."
    tradeoffs:
      - "o mais barato"
      - "criterio sem gate e o que deixou a camada agentic-sf entrar: nada acusou por um mes"
chosen: A
---

# CRITERIO_DE_DOMINIO — exploração

## Origem

Quarta das frentes da avaliação de 2026-09-17: domínio novo entra por **artefato
coletável**, nunca por nome de agente. SF_STUBS (PR #88) removeu a camada que entrou
sem artefato; esta feature impede que ela volte.

## Perfil

`dev`. Branch `sdd/criterio-de-dominio`, empilhada sobre `sdd/sf-stubs` (#88).

## Medidas (2026-09-19, sobre `99ae3eaf`)

- O que já tem gate, por regra: kind exigido sem extrator exige `blocked_on`
  (`tests/test_rules_catalog_reachability.py::test_kind_exigido_tem_extrator_ou_a_regra_declara_blocked_on`);
  regra executável sem fixture que a dispare cai em `tests/test_fixtures_kind_coverage.py`;
  área sem coordenador cai em `tests/test_agent_coverage.py::test_no_area_is_orphan`;
  área sem rota em `tests/test_router_agents.py`.
- O que não tem gate:
  - área só com regra `executable: false` (o loader aceita, e era a camada `agentic-sf-*`);
  - coordenador sem área que julga (o teste do SF_STUBS cobre só `sf-*`, e pela lista);
  - coordenador só alcançável por rota `__agentic_*__`.
- Hoje nenhuma área tem `blocked_on` em todas as regras.
- Rotas por coordenador: 12 dos 19 têm rota que dispara por finding. Os sete restantes
  (`sf-analytics-specialist`, `sf-graph-specialist`, `sf-neptune-specialist`,
  `sf-orchestrator`, `sf-pyspark-specialist`, `sf-storage-specialist`,
  `sf-token-verifier`) só têm rota `__agentic_*__`. Seis desses repetem áreas de um
  coordenador clássico: SF-PY e SF-PLAN (`pyspark-code-reviewer`), SF-ICE e SF-PQ
  (`iceberg-performance-engineer`), SF-DQ (`data-quality-reviewer`) e SF-GRAPH
  (`pyspark-code-reviewer`).

## Perguntas feitas

1. O pedido do operador (2026-09-19) foi fazer SF_STUBS e CRITERIO_DE_DOMINIO em
   sequência.
2. Qual abordagem? Resposta (2026-09-19): A, gate nos três níveis.

## Abordagens

A (recomendada) põe gate nos três níveis e decide os sete. B deixa o modo
`__agentic_*__` como opt-in legítimo. C é só texto.

## Escolha

A, escolhida pelo operador: é a única em que as três portas pelas quais a camada
`agentic-sf` entrou (área sem regra que julga, coordenador sem domínio, rota que só um
nome aciona) caem num teste.
