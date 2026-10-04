---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_PROGRESS_OBSERVABILITY_DEPTH/define.md
  sha256: "3809b9f099e0c644969bde481f0c1a16f239f6e208dacdadb67ae334b4ce4d1d"
files:
  - {path: sparkforge/facts/streaming.py, action: modify, reason: "agregar span temporal, duração, memória do state e watermark com unresolved explícito"}
  - {path: rules/catalog/streaming.yaml, action: modify, reason: "adicionar findings para watermark parado e crescimento de memória observado"}
  - {path: tests/test_facts_streaming.py, action: modify, reason: "provar resumo e lacunas temporais antes do código"}
  - {path: tests/test_streaming_rules.py, action: modify, reason: "provar runtime/evidence gates das regras novas"}
  - {path: tests/test_fixtures_golden_streaming.py, action: modify, reason: "cobrir fixture temporal e regressão dos goldens"}
  - {path: fixtures/streaming/progress_watermark_stalled, action: create, reason: "golden de watermark estacionado e memória do state crescente"}
  - {path: fixtures/streaming/progress_positive, action: modify, reason: "regenerar medidas adicionais sem alterar findings"}
  - {path: fixtures/streaming/progress_runtime_divergent, action: modify, reason: "regenerar resumo temporal sob divergência de runtime"}
  - {path: knowledge/streaming-reliability.md, action: modify, reason: "documentar medidas compactas e limites dos sintomas"}
  - {path: skills/review-structured-streaming/SKILL.md, action: modify, reason: "ensinar leitura dos novos fatos sem causa presumida"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "atualizar Structured Streaming e observability gaps"}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "cobrir documentação da profundidade de progress"}
decisions:
  - id: D1
    choice: "Manter streaming.progress.series como envelope compacto e adicionar apenas medidas/attrs derivados de campos públicos do progress."
    rejected: ["criar analyzer paralelo", "emitir um fact por percentil ou por batch, que aumentaria payload e contexto"]
    rollback: "Reverter o resumo e as duas regras; facts batch/source/sink/event_time/state_operator continuam compatíveis."
  - id: D2
    choice: "Calcular span com timestamps ISO timezone-aware e watermark com eventTime.watermark; qualquer valor inválido gera unresolved nomeado."
    rejected: ["usar ordem do arquivo como relógio", "tratar watermark ausente como epoch ou zero", "inferir freshness"]
    rollback: "Remover somente attrs/medidas derivadas e conservar as observações brutas."
  - id: D3
    choice: "Somar memória dos operadores somente quando todos os operadores do batch fornecerem numeração válida; flags de crescimento são sintomas observados."
    rejected: ["somar apenas operadores legíveis", "usar limiar absoluto de bytes", "declarar leak de state"]
    rollback: "Retirar state_memory_growth_observed e manter state rows já existente."
covers:
  - {part: "progress series", acceptance: [AC1, AC2]}
  - {part: "catalog rules", acceptance: [AC3, AC5]}
  - {part: "fixtures", acceptance: [AC4]}
  - {part: "knowledge and skill", acceptance: [AC6]}
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — desenho

## Conhecimento consultado

- `sparkforge rules lookup --category streaming`: regras atuais SF-STREAM-001 a
  SF-STREAM-003 exigem runtime e série observada; elas não autorizam causa.
- `knowledge/streaming-reliability.md`: separa progress, transporte, state,
  watermark e sink, e declara que uma amostra não sustenta tendência.
- `sparkforge/facts/streaming.py`: já emite fatos públicos de batch, event time
  e state operator; o novo resumo não lê checkpoint interno nem chama provider.
- `prompt_evo_streaming.md`, seções 7, 8, 19, 24, 40, 44 e 50: exige facts
  temporais compactos, unresolved, regras evidence-first e economia de contexto.
