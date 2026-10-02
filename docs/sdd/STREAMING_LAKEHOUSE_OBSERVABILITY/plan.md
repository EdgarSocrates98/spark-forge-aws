---
sdd: 1
feature: STREAMING_LAKEHOUSE_OBSERVABILITY
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_LAKEHOUSE_OBSERVABILITY/design.md
  sha256: "74e679129ba64084adbd328f388a64bf9291d6f0112e0d6fc3ccdacff66f9587"
tasks:
  - {id: T1, files: [tests/test_facts_streaming_composition.py, sparkforge/facts/streaming_composition.py], covers: [AC1, AC2], test: {path: tests/test_facts_streaming_composition.py, name: test_iceberg_link_requires_declared_identity}}
  - {id: T2, files: [fixtures/streaming_composition, tests/test_fixtures_golden_streaming_composition.py, scripts/regen_streaming_composition_fixtures.py, rules/catalog/streaming_composition.yaml], covers: [AC3], test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_corpus_is_complete}}
  - {id: T3, files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_streaming_composition.py], covers: [AC4], test: {path: tests/test_analyze_streaming_composition.py, name: test_cli_and_mcp_envelopes_match}}
  - {id: T4, files: [skills/analyze-streaming-composition/SKILL.md, agents/streaming-realtime-architect.md, rules/catalog/routing.yaml, parity.yaml, manifest.json, docs/streaming/prompt-coverage.md], covers: [AC5], test: {path: tests/test_capability_parity.py, name: "TestManifestMatchesReality::test_every_declared_tool_exists_in_the_tool_surface"}}
---

# STREAMING_LAKEHOUSE_OBSERVABILITY — plano

Implementar o compositor e seus testes antes da superfície; criar goldens a
partir do mesmo builder; depois publicar CLI/MCP, skill, routing e gates.
