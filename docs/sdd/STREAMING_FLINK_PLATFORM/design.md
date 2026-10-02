---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_PLATFORM/define.md
  sha256: "67751fe8f9b33d4c50df63a829b10d64c797363e7c0ca1eab6fdd6fa2ef9df46"
files:
  - {path: sparkforge/facts/flink.py, action: create, reason: "extrator JSON/JSONL offline para Flink e Managed Flink"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "expor analyzer e envelope"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar analyze flink"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar tool MCP"}
  - {path: rules/catalog/flink.yaml, action: create, reason: "findings apenas para checkpoint falho e backpressure observado"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rota SF-FLINK para especialista streaming"}
  - {path: fixtures/flink, action: create, reason: "goldens Flink e Managed Flink"}
  - {path: knowledge/flink-streaming.md, action: create, reason: "semântica, limites e fontes oficiais"}
  - {path: .agents/skills/analyze-flink-job/SKILL.md, action: create, reason: "workflow evidence-first"}
  - {path: agents/streaming-realtime-architect.md, action: create, reason: "coordenador para streaming/Flink"}
  - {path: parity.yaml, action: modify, reason: "capability e caminhos de execução"}
  - {path: docs/surface.lock.json, action: modify, reason: "surface regenerada"}
decisions:
  - id: D1
    choice: "Um analyzer com artifact obrigatório flink|managed_flink e namespaces separados."
    rejected: ["um namespace compartilhado que misturaria upstream e serviço AWS"]
    rollback: "Reverter o commit do analyzer e remover a tool Flink."
  - id: D2
    choice: "Facts literais; ausência de série ou métrica vira unresolved."
    rejected: ["threshold fixo de backpressure", "zero default para métrica ausente"]
    rollback: "Reverter facts/rules e remover as fixtures que dependem do contrato."
  - id: D3
    choice: "Rules só para checkpoint explicitamente falho e backpressure medido."
    rejected: ["diagnosticar lentidão pela presença do campo operator", "inferir custo"]
    rollback: "Reverter rules e rota; manter analyzer somente se a superfície continuar necessária."
covers:
  - {part: "facts Flink", acceptance: [AC1, AC2]}
  - {part: "fixtures e rules", acceptance: [AC3, AC4]}
  - {part: "surface e especialistas", acceptance: [AC5]}
---

# STREAMING_FLINK_PLATFORM — desenho

O contrato usa o mesmo envelope de facts do repositório e adiciona a distinção
de serviço no `artifact` e no `kind`. Checkpoint, state e backpressure são
medidas observadas; o analyzer não interpreta ausência como saúde.
