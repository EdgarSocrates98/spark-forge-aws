---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_PROGRESS_OBSERVABILITY_DEPTH/design.md
  sha256: "75bec8852eeab24ead2e7f2cc741b4bf7c0a5bcf24a8afe29f2ff9520477da21"
tasks:
  - id: T1
    files: [tests/test_facts_streaming.py, sparkforge/facts/streaming.py]
    covers: [AC1, AC2]
    test: {path: tests/test_facts_streaming.py, name: test_progress_series_summarizes_temporal_state_and_watermark}
  - id: T2
    files: [rules/catalog/streaming.yaml, tests/test_streaming_rules.py]
    covers: [AC3, AC5]
    test: {path: tests/test_streaming_rules.py, name: test_progress_observability_depth_rules_are_evidence_first}
  - id: T3
    files: [fixtures/streaming/progress_watermark_stalled, fixtures/streaming/progress_positive, fixtures/streaming/progress_runtime_divergent, tests/test_fixtures_golden_streaming.py]
    covers: [AC4]
    test: {path: tests/test_fixtures_golden_streaming.py, name: TestGolden::test_facts_match_golden}
  - id: T4
    files: [knowledge/streaming-reliability.md, skills/review-structured-streaming/SKILL.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_progress_observability_depth_coverage}
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — plano

Executar T1–T4 em sequência. T1 começa pelos testes node-level de resumo e
lacuna temporal; T2 adiciona rules e verifica runtime/evidence gates; T3 cria e
regenera o golden; T4 documenta o contrato, sincroniza mirrors e fecha gates.
Suíte completa fica fora desta frente; serão executados lotes
focados e os gates derivados da mudança.
