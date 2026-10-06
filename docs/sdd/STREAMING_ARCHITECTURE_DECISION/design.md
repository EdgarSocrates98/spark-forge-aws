---
sdd: 1
feature: STREAMING_ARCHITECTURE_DECISION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ARCHITECTURE_DECISION/define.md
  sha256: "7aeaae1c2373c03a7c8320b70999d9e1dbdf9cae9828d3dbf6da29ca030c96a0"
files:
  - {path: sparkforge_aws/architecture/streaming.py, action: create, reason: "matriz e eliminação offline"}
  - {path: sparkforge_aws/architecture/__init__.py, action: create, reason: "publicar helper do domínio"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "adicionar architecture streaming CLI-only"}
  - {path: tests/test_streaming_architecture.py, action: create, reason: "fixtures, recusa de empate e smoke CLI"}
  - {path: fixtures/realtime_architecture, action: create, reason: "casos ambiguous, unique e insufficient"}
  - {path: knowledge/streaming-realtime-candidate-matrix.md, action: create, reason: "matriz e fontes primárias"}
  - {path: skills/design-realtime-data-architecture/SKILL.md, action: create, reason: "workflow de decisão evidence-first"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "declarar skill de decisão"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "auditar arquitetura decision support"}
decisions:
  - id: D1
    choice: "Comando CLI-only; nenhuma tool MCP nova nesta wave."
    rejected: ["crescer superfície MCP sem contrato de output requerido", "misturar com Decision Plane de roteamento"]
    rollback: "Remover parser, módulo, fixtures e skill mantendo knowledge como referência."
  - id: D2
    choice: "Selecionar somente quando exatamente um candidato for suportado."
    rejected: ["ranking por preferência", "score de custo sem medida", "desempate implícito"]
    rollback: "Forçar ADR unresolved até existir constraint nova e verificável."
  - id: D3
    choice: "Sink candidates são avaliados como papel separado e não substituem runtime."
    rejected: ["tratar Iceberg/Redshift como engine de processamento"]
    rollback: "Separar novamente runtime e serving no input."
covers:
  - {part: "requirements/assumptions", acceptance: [AC1]}
  - {part: "candidate matrix/constraints", acceptance: [AC2, AC3]}
  - {part: "ADR and CLI", acceptance: [AC4]}
  - {part: "knowledge/skill/integration", acceptance: [AC5]}
---

# STREAMING_ARCHITECTURE_DECISION — desenho

O retorno traz workload profile, candidate matrix, constraint elimination,
decision, ADR e unresolved. O hash do input torna a avaliação reprodutível;
não representa versão de runtime nem assinatura de aprovação.
