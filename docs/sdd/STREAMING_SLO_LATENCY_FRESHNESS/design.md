---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_LATENCY_FRESHNESS/define.md
  sha256: "fb6cb695fbdd8d2a5c5fcda63f644675038c0559ff2fefb88c5692fdbf7abf8c"
files:
  - {path: sparkforge/facts/streaming_ops.py, action: modify, reason: "preservar statistic seguro na declaração SLO"}
  - {path: sparkforge/facts/streaming.py, action: modify, reason: "emitir freshness_ms somente de timestamp/eventTime.max ou campo explícito"}
  - {path: sparkforge/facts/streaming_slo.py, action: modify, reason: "aceitar métricas de latência, statistic=p95 e cálculo nearest-rank"}
  - {path: tests/test_facts_streaming_ops.py, action: modify, reason: "provar contrato seguro de statistic"}
  - {path: tests/test_facts_streaming.py, action: modify, reason: "provar freshness temporal e unresolved"}
  - {path: tests/test_facts_streaming_slo.py, action: modify, reason: "provar p95, freshness e end-to-end explícito"}
  - {path: tests/test_fixtures_golden_streaming_composition.py, action: modify, reason: "incluir golden p95/freshness"}
  - {path: fixtures/streaming_composition/slo_p95_freshness, action: create, reason: "contrato e progress com freshness observada e p95"}
  - {path: knowledge/streaming-operations.md, action: modify, reason: "documentar SLI p95/freshness e limites semânticos"}
  - {path: skills/review-structured-streaming/SKILL.md, action: modify, reason: "orientar leitura de freshness e p95"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "registrar fechamento offline parcial do gap p95/freshness"}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "cobrir documentação da nova avaliação"}
decisions:
  - id: D1
    choice: "Reusar streaming.slo.evaluation e o modo=slo existente; statistic é atributo de declaração e não nova tool."
    rejected: ["criar namespace/mcp novo", "emitir um fact por percentil"]
    rollback: "Reverter apenas attrs/measures de p95/freshness; avaliação all e fontes anteriores permanecem compatíveis."
  - id: D2
    choice: "Derivar freshness por batch de timestamp - eventTime.max, ambos ISO timezone-aware; aceitar freshnessMs explícito como observação já medida."
    rejected: ["usar eventTime.avg", "usar watermark como freshness", "usar ordem do arquivo", "usar batchDuration como end-to-end"]
    rollback: "Remover medidas de freshness e preservar batch/event_time brutos."
  - id: D3
    choice: "Nearest-rank p95 com rank=ceil(0.95*n), sem interpolação; status compara somente valor agregado."
    rejected: ["média móvel", "interpolação implícita", "threshold mínimo inventado"]
    rollback: "Desabilitar statistic=p95 e manter comparação individual."
covers:
  - {part: "SLO declaration", acceptance: [AC1]}
  - {part: "progress freshness", acceptance: [AC2, AC4]}
  - {part: "SLO composition", acceptance: [AC3]}
  - {part: "golden and docs", acceptance: [AC5, AC6]}
---

# STREAMING_SLO_LATENCY_FRESHNESS — desenho

## Conhecimento consultado

- `sparkforge/facts/streaming.py`: `StreamingQueryProgress` público já traz
  `timestamp` e `eventTime`; o extractor preserva ambos como facts.
- `sparkforge/facts/streaming_slo.py`: seleção por identidade, unidade,
  timestamp, cobertura de janela e proveniência já são contratos estáveis.
- `knowledge/streaming-operations.md`: SLO não escolhe target e não confunde
  ausência de evidência com atendimento.
- `prompt_evo_streaming.md`, seções 19, 20, 40, 44 e 50: exige freshness,
  p95, unresolved e separação entre offline e live.
