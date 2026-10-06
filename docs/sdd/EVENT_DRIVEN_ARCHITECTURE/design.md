---
sdd: 1
feature: EVENT_DRIVEN_ARCHITECTURE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/EVENT_DRIVEN_ARCHITECTURE/define.md
  sha256: "5f2e5495a54a459466712150e5cc993f0fa0d67eba21be35979af816e02a70b7"
files:
  - {path: sparkforge_aws/facts/event_driven.py, action: create, reason: "extrair configuração EventBridge/Pipes/SQS/SNS sem rede"}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "expor analyzer compartilhado"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "adicionar analyze event-driven"}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "adicionar tool MCP read-only"}
  - {path: rules/catalog/event-driven.yaml, action: create, reason: "findings de DLQ/redrive e target ausente"}
  - {path: fixtures/event_driven, action: create, reason: "goldens de contrato e lacunas"}
  - {path: skills/review-event-driven-architecture/SKILL.md, action: create, reason: "workflow evidence-first"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "declarar SF-EVENT"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rotear findings ao especialista streaming"}
  - {path: knowledge/event-driven-architecture.md, action: create, reason: "contrato e limites operacionais"}
  - {path: parity.yaml, action: modify, reason: "registrar capability"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "auditar Wave H"}
decisions:
  - id: D1
    choice: "JSON salvo como entrada única do extractor."
    rejected: ["chamada AWS dentro do core", "inferência de estado por nome"]
    rollback: "Reverter extractor/tool e remover a capability dos manifestos."
  - id: D2
    choice: "Campos ausentes continuam não declarados e seções inválidas viram unresolved."
    rejected: ["false/zero default para retry, DLQ ou target"]
    rollback: "Remover rules dependentes e preservar apenas facts comprovados."
  - id: D3
    choice: "Rules estruturais têm ação, evidência, validação e rollback, sem claims de incidente."
    rejected: ["finding de exactly-once ou perda baseado em configuração"]
    rollback: "Reverter catálogo e manter analyzer somente factual."
covers:
  - {part: "EventBridge rules/Pipes", acceptance: [AC1, AC2]}
  - {part: "SQS/SNS delivery contract", acceptance: [AC1, AC3]}
  - {part: "CLI/MCP and integration gates", acceptance: [AC4, AC5]}
---

# EVENT_DRIVEN_ARCHITECTURE — desenho

O extractor mantém a separação fato/julgamento. Regras só usam atributos e
medidas presentes no Fact; o caminho para investigar execução permanece no
runbook e nos próximos collectors, fora desta wave.
