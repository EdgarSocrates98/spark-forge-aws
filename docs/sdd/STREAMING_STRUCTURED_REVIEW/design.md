---
sdd: 1
feature: STREAMING_STRUCTURED_REVIEW
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_STRUCTURED_REVIEW/define.md
  sha256: "947f400bbd6d7a2748f8e2e50214782f42dbecbc6f1e166a70dc4dc52f23a9ab"
files:
  - {path: skills/review-structured-streaming/SKILL.md, action: create, reason: "workflow evidence-first de Structured Streaming"}
  - {path: skills/review-structured-streaming/evals/evals.json, action: create, reason: "evals de série e semântica de checkpoint"}
  - {path: skills/review-structured-streaming/references/README.md, action: create, reason: "ponte para knowledge local"}
  - {path: skills/review-structured-streaming/scripts/validate_evidence.py, action: create, reason: "validador mínimo de fact_id"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "declarar skill dedicada"}
  - {path: sparkforge_aws/integrate/render.py, action: modify, reason: "registrar skill como dispatchable"}
  - {path: tests/test_sync_render.py, action: modify, reason: "fixar coordenador único"}
decisions:
  - id: D1
    choice: "Reutilizar analyzers e rules existentes; skill só orquestra o workflow."
    rejected: ["duplicar extractor", "criar regra por recomendação textual"]
    rollback: "Remover skill e sua referência do coordenador; facts permanecem."
  - id: D2
    choice: "Despacho read-only fechado; AWS live e mutações ficam fora."
    rejected: ["dar acesso de escrita ao subagente", "inferir métrica ausente"]
    rollback: "Mover skill para NON_DISPATCHABLE_SKILLS se a fronteira mudar."
covers:
  - {part: "source/progress/checkpoint review", acceptance: [AC1]}
  - {part: "eval and evidence contract", acceptance: [AC2]}
  - {part: "agent/mirror routing", acceptance: [AC3]}
  - {part: "counts and regression", acceptance: [AC4]}
---

# STREAMING_STRUCTURED_REVIEW — design
