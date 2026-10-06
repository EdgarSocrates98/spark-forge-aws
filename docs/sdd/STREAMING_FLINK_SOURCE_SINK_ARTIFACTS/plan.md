---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_SOURCE_SINK_ARTIFACTS/design.md
  sha256: "065e2adbff9a76605036f9574551891d523a7925e88d6f041f33f81121d423da"
tasks:
  - id: T1
    files: [tests/test_facts_flink.py, sparkforge_aws/facts/flink.py]
    covers: [AC1, AC2, AC3, AC4]
    test: {path: tests/test_facts_flink.py, name: test_flink_dump_emits_explicit_source_and_sink}
  - id: T2
    files: [fixtures/flink/flink_positive/input/dump.json, scripts/regen_flink_fixtures.py, fixtures/flink]
    covers: [AC1, AC3, AC5]
    test: {path: tests/test_fixtures_golden_flink.py, name: test_flink_fixture_corpus_is_complete}
  - id: T3
    files: [knowledge/flink-streaming.md, skills/analyze-flink-job/SKILL.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_flink_source_sink_artifacts_coverage}
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — plano

Implementação serializada: escrever testes vermelhos para objeto/lista,
aliases, ausência e isolamento Managed Flink; implementar parser; adicionar
source/sink ao fixture positivo e regenerar goldens; atualizar documentação,
referências, mirrors e números; executar gates focados. Não rodar suite total.

## T1 — parser e contrato

Adicionar helpers pequenos no extrator existente. O parser deve normalizar
objeto para lista, emitir facts somente quando há atributo ou medida observada,
e usar unresolved nomeado para ausência ou formato inválido. Testar que campos
ausentes não aparecem em `measures`.

## T2 — corpus

Adicionar source Kafka e sink Iceberg ao fixture positivo, com backlog e
pending_commits somente como valores observados. Regenerar todos os goldens pelo
script oficial e verificar kinds no inventário de fixtures.

## T3 — documentação e gates

Documentar o contrato em knowledge, skill, guia/referência, prompt coverage,
README/status/ledger se necessário; rodar geradores oficiais, SDD check,
surface lock, offline bundle, sync skills e testes focados. Não declarar ganho
de performance nem saúde operacional.
