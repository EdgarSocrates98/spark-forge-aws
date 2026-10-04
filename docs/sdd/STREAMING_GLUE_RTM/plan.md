---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RTM/design.md
  sha256: "6237f2a56d367ae145f44b757f402449bcfd8916272ec752ff448e5d6cc740e1"
tasks:
  - {id: T1, files: [tests/test_facts_glue_streaming.py, sparkforge/facts/glue_streaming.py], covers: [AC1], test: {path: tests/test_facts_glue_streaming.py, name: test_rtm_dump_emits_observed_constraints_and_capacity}}
  - {id: T2, files: [fixtures/glue_streaming, tests/test_fixtures_golden_glue_streaming.py, scripts/regen_glue_streaming_fixtures.py, rules/catalog/glue-streaming.yaml], covers: [AC2], test: {path: tests/test_fixtures_golden_glue_streaming.py, name: test_glue_streaming_fixture_corpus_is_complete}}
  - {id: T3, files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_glue_streaming.py], covers: [AC3], test: {path: tests/test_analyze_glue_streaming.py, name: test_cli_and_mcp_glue_streaming_envelopes_match}}
  - {id: T4, files: [skills/review-glue-streaming/SKILL.md, agents/streaming-realtime-architect.md, sparkforge/integrate/render.py, rules/catalog/routing.yaml, parity.yaml, manifest.json], covers: [AC4], test: {path: tests/test_capability_parity.py, name: "TestManifestMatchesReality::test_every_declared_tool_exists_in_the_tool_surface"}}
---

# STREAMING_GLUE_RTM — plano

Implementar fatos e fixtures antes da integração de superfície; depois publicar
CLI/MCP, skill, especialista, routing, parity e regenerar os registros derivados.
