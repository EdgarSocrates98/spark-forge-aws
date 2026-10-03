---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_SOURCE_SINK_ARTIFACTS/design.md
  sha256: "29de989529b2eda32a53280bd3d3f55a981d12f4844e853dadd54a5ec02af1aa"
tasks:
  - id: T1
    files: [tests/test_facts_glue_streaming.py, sparkforge/facts/glue_streaming.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_glue_streaming.py, name: test_stream_endpoints_emit_explicit_facts}
  - id: T2
    files: [fixtures/glue_streaming, scripts/regen_glue_streaming_fixtures.py, tests/test_fixtures_golden_glue_streaming.py]
    covers: [AC4]
    test: {path: tests/test_fixtures_golden_glue_streaming.py, name: test_glue_streaming_fixture_corpus_is_complete}
  - id: T3
    files: [knowledge/glue-streaming-rtm.md, skills/review-glue-streaming/SKILL.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC5]
    test: {path: tests/test_docs_coverage.py, name: test_glue_source_sink_artifacts_coverage}
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — plano

Implementação serializada: testes vermelhos para objeto/lista, aliases,
whitelist e unresolved; parser; fixture positivo e goldens; docs, referências,
mirrors e números; gates focados. Suite total fica fora desta fase.

## T1 — parser e contrato

Adicionar helper pequeno ao extrator existente. Não copiar estruturas
aninhadas. Emitir fact se houver atributo ou medida observada; emitir unresolved
quando bloco/registro não puder sustentar o contrato.

## T2 — corpus

Adicionar source Kafka e sink Iceberg ao fixture positivo com medidas apenas
observadas; regenerar goldens pelo script oficial; declarar kinds nas metas.

## T3 — documentação e gates

Atualizar knowledge, skill, guias, README, prompt coverage, índice, SDD e
ledgers. Rodar geradores, SDD check, surface/offline/sync/status gates e testes
focados. Não declarar ganho ou saúde operacional.
