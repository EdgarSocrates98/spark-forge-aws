---
sdd: 1
feature: AGENTIC_ENGINEERING_OS_V2
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Evolução vertical local-first sobre os contratos existentes, com trust, memória, economia, routing, AgentOps e Forge protocol em módulos pequenos e opt-in."
    tradeoffs:
      - "reaproveita Evidence, Context Gateway, ContextLedger, Decision Plane e traces existentes"
      - "entrega contratos e observabilidade determinística sem prometer live-model gains"
      - "exige adaptadores de compatibilidade em vez de substituir APIs legadas"
  - id: B
    summary: "Reescrita transversal para um kernel agentic único e migração de todos os consumidores."
    tradeoffs:
      - "poderia reduzir duplicação depois da migração"
      - "alto risco de quebrar CLI/MCP parity, local-first e histórico de traces"
      - "não permite atribuir regressão a uma variável por onda"
  - id: C
    summary: "Adicionar somente documentação e roadmap, deixando execução para fases futuras."
    tradeoffs:
      - "baixo risco imediato"
      - "não entrega enforcement de memory write, trust propagation, economics ou AgentOps"
      - "mantém gaps já identificados na auditoria"
chosen: A
---

# AGENTIC_ENGINEERING_OS_V2 — exploração

## Perfil

`dev`: mudança no próprio SparkForge. Requisito do operador já está explícito em
`prompt_evo_new_step1.md`; explore registra alternativas e limites antes do build.

## Auditoria inicial

O repositório já possui camada determinística de facts/rules/findings, Context
Gateway, Code Intelligence, Decision Plane, ContextLedger, traces SQLite,
economy router, security guardrails, workflow handoff, Forge Lab, evals e
adapters CLI/MCP. Gaps verificáveis para esta entrega:

- `sparkforge.agentic.memory` registra decisão sem candidate/trust/outcome gate e
  recupera somente por overlap de palavras;
- não há envelope público que carregue origin, trust, taint,
  instruction_authority, scope e freshness por unidade de contexto;
- `StructuredHandoff` não separa facts, assumptions, hypotheses e
  requested_action com isolamento de instrução;
- bytes de tool, tokens observados, budgets e custo ainda não têm um ledger
  comum com reconciliação estimado/observado;
- router existente escolhe tier por regras fixas, sem scorecard de modelo e
  modo shadow/assisted/active independente de case routing;
- traces podem ser lidos, mas não há AgentOps inspect/compare/baseline nem
  detector de desperdício com atribuição observada/estimada/hipótese;
- não há protocolo público mínimo para interoperabilidade Forge/A2A nem
  checkpoint semântico content-addressed.

## Abordagens consideradas

`A` foi escolhida porque cobre os gaps sem duplicar capabilities existentes. A
entrega mantém APIs legadas, não exige vector database, não chama provider no
core, não habilita active routing por default e deixa números econômicos sem
fonte como `unresolved`.

## Critério de parada

Esta feature entrega contratos locais, enforcement, comandos de inspeção e
documentação. Live-model evals, benchmark de custo real, integração AWS e
promoção para active dependem de transcript/execuções externas e ficam
explicitamente `unresolved` até haver evidência.

## Cobertura do prompt_evo_new_step1.md

| Faixa do prompt | Entrega correspondente | Estado verificável |
|---|---|---|
| 0–2: base, memória e confiança | `trust.py`, memória estruturada/quarentena, papéis e handoff | implementado; provider/AWS ausentes permanecem `unresolved` |
| 3–4: contexto e economia | `context/quality.py`, ledger reconciliado, router shadow/assisted/active | implementado; tokens/custo sem fonte não são inferidos |
| 5–7: execução e observabilidade | checkpoint semântico, protocolos Forge, AgentOps inspect/compare/baseline | implementado; baseline é escrita local idempotente |
| 8–10: superfície e compatibilidade | CLI, MCP, parity, referências geradas, doctor | implementado; superfície existente preservada |
| 11–13: documentação, governança e entrega | ADR, ledger, status, claims, SDD e rollback por onda | implementado; gates e suíte final pendentes até ship |

Esta matriz fecha rastreabilidade funcional sem transformar benchmark hipotético,
integração externa ou promoção de modelo em fato.
