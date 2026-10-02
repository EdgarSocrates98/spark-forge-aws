---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_PLATFORM/design.md
  sha256: "b4ddfecd2c6554d5e29e28220f5a42f7e43b3b674f14791d13b40360936ce2d8"
tasks:
  - {id: T1, files: [tests/test_facts_flink.py, sparkforge/facts/flink.py], covers: [AC1, AC2], test: {path: tests/test_facts_flink.py, name: test_flink_dump_emits_job_operator_checkpoint_state}}
  - {id: T2, files: [fixtures/flink, tests/test_fixtures_golden_flink.py, scripts/regen_flink_fixtures.py, rules/catalog/flink.yaml, knowledge/flink-streaming.md], covers: [AC3], test: {path: tests/test_fixtures_golden_flink.py, name: test_flink_fixture_corpus_is_complete}}
  - {id: T3, files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_flink.py], covers: [AC4], test: {path: tests/test_analyze_flink.py, name: test_cli_and_mcp_flink_envelopes_match}}
  - {id: T4, files: [skills/analyze-flink-job/SKILL.md, agents/streaming-realtime-architect.md, sparkforge/integrate/render.py, rules/catalog/routing.yaml, parity.yaml, manifest.json, tests/test_capability_parity.py], covers: [AC5], test: {path: tests/test_capability_parity.py, name: "TestManifestMatchesReality::test_every_declared_tool_exists_in_the_tool_surface"}}
---

# STREAMING_FLINK_PLATFORM — plano

Implementar facts e testes antes da superfície, criar goldens e rules com
evidência medida, depois publicar CLI/MCP, especialista, parity e referências.
