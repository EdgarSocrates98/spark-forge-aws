---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RTM/define.md
  sha256: "a2a5ecab700f0bd69f467b168a11ee238c5d8d975d926dde51cbd97d2d8c4ada"
files:
  - {path: sparkforge/facts/glue_streaming.py, action: create, reason: "extrator JSON/JSONL offline de jobs Glue Streaming/RTM"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "envelope comum para analyzer Glue Streaming"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar analyze glue-streaming"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar tool MCP read-only"}
  - {path: rules/catalog/glue-streaming.yaml, action: create, reason: "rules de restrições RTM e capacidade ausente"}
  - {path: fixtures/glue_streaming, action: create, reason: "goldens válido, incompatível e unresolved"}
  - {path: skills/review-glue-streaming/SKILL.md, action: create, reason: "workflow evidence-first para Glue Streaming/RTM"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "cobrir Glue Streaming e área SF-GLUE-STREAM"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rotear achados para especialista streaming"}
  - {path: parity.yaml, action: modify, reason: "declarar caminhos de execução"}
decisions:
  - id: D1
    choice: "Namespace glue.streaming.* com modo explícito REAL_TIME ou MICRO_BATCH."
    rejected: ["misturar com flink.* ou streaming.*", "inferir modo somente pelo nome do comando"]
    rollback: "Reverter analyzer, rules e fixtures Glue; manter apenas conhecimento documentado."
  - id: D2
    choice: "Ausência de restrição ou capacidade emite unresolved e impede findings dependentes."
    rejected: ["zero default", "inferir task slots de workers"]
    rollback: "Reverter facts/rules e remover goldens que dependem do contrato."
  - id: D3
    choice: "Rules cobrem somente incompatibilidades declaradas e observadas."
    rejected: ["afirmar causalidade ou ganho de latência", "coletar AWS dentro do core"]
    rollback: "Reverter rules e routing; analyzer pode permanecer como extração offline."
covers:
  - {part: "facts e unresolved", acceptance: [AC1]}
  - {part: "fixtures e rules", acceptance: [AC2]}
  - {part: "CLI/MCP", acceptance: [AC3]}
  - {part: "skill, agente e registros", acceptance: [AC4]}
---

# STREAMING_GLUE_RTM — desenho
