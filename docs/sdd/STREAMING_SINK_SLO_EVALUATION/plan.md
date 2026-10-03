---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SINK_SLO_EVALUATION/design.md
  sha256: "60cc757bc988c280f683a6b0ad19d4ea8fce90a9bf96797ce86f13f513757e9a"
tasks:
  - id: T1
    files: [tests/test_facts_streaming_slo.py, sparkforge/facts/streaming_slo.py, sparkforge/facts/streaming_ops.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_streaming_slo.py, name: test_evaluates_sink_output_slo}
  - id: T2
    files: [sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_streaming_composition.py]
    covers: [AC4]
    test: {path: tests/test_analyze_streaming_composition.py, name: test_sink_slo_cli_and_mcp_envelopes_match}
  - id: T3
    files: [fixtures/streaming_composition, tests/test_fixtures_golden_streaming_composition.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_goldens}
  - id: T4
    files: [skills/analyze-streaming-composition/SKILL.md, knowledge/streaming-operations.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_sink_slo_coverage_mentions_batch_link}
  - id: T5
    files: [docs/surface.lock.json, knowledge/offline-manifest.json, manifest.json]
    covers: [AC6]
    test: {path: tests/test_surface_lock.py, name: TestOLockBateComAMedida::test_the_tool_catalogue_matches}
---

# STREAMING_SINK_SLO_EVALUATION — plano

Executar T1–T5. T1 começa pelos testes de identidade, vínculo temporal,
unidade, cobertura e ambiguidade. T2 mantém core, CLI e MCP no mesmo caminho.
T3 cria goldens. T4 documenta evidência e limites. T5 regenera metadados e
fecha gates. Suíte completa continua fora desta frente.
