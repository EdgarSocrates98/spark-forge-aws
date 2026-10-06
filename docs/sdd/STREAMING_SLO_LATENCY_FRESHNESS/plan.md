---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_LATENCY_FRESHNESS/design.md
  sha256: "0b0d2358127cb92da2545d38230c0b8d1c861329717b830c0ac06e82b50330dd"
tasks:
  - id: T1
    files: [tests/test_facts_streaming_ops.py, sparkforge_aws/facts/streaming_ops.py, tests/test_facts_streaming.py, sparkforge_aws/facts/streaming.py]
    covers: [AC1, AC2, AC4]
    test: {path: tests/test_facts_streaming.py, name: test_progress_derives_freshness_only_from_event_time_max}
  - id: T2
    files: [tests/test_facts_streaming_slo.py, sparkforge_aws/facts/streaming_slo.py]
    covers: [AC3, AC4]
    test: {path: tests/test_facts_streaming_slo.py, name: test_evaluates_p95_freshness_slo}
  - id: T3
    files: [fixtures/streaming_composition/slo_p95_freshness, tests/test_fixtures_golden_streaming_composition.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_goldens}
  - id: T4
    files: [knowledge/streaming-operations.md, skills/review-structured-streaming/SKILL.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_slo_latency_freshness_coverage}
---

# STREAMING_SLO_LATENCY_FRESHNESS — plano

Executar T1–T4 em sequência. T1 começa com testes node-level e contrato de
declaração; T2 implementa composição p95; T3 cria e regenera golden; T4
documenta o contrato, sincroniza mirrors e fecha gates. Suíte completa fica
fora desta frente; executar apenas lotes focados e gates derivados da mudança.
