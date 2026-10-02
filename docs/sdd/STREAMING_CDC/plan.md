---
sdd: 1
feature: STREAMING_CDC
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_CDC/design.md
  sha256: "dd3d26906c4793414b487f506eddb7b8a9bf605da582ec34c8ba3a5fd6a02932"
tasks:
  - {id: T1, files: [sparkforge/facts/cdc.py, tests/test_facts_cdc.py], covers: [AC1, AC2], test: {path: tests/test_facts_cdc.py, name: test_cdc_events_preserve_position_transaction_delete_and_duplicate}}
  - {id: T2, files: [fixtures/cdc, rules/catalog/cdc.yaml, scripts/regen_cdc_fixtures.py, tests/test_fixtures_golden_cdc.py, tests/test_cdc_rules.py], covers: [AC3], test: {path: tests/test_fixtures_golden_cdc.py, name: test_cdc_fixture_corpus_is_complete}}
  - {id: T3, files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_cdc.py], covers: [AC4], test: {path: tests/test_analyze_cdc.py, name: test_cli_and_mcp_cdc_envelopes_match}}
  - {id: T4, files: [skills/review-cdc-replication/SKILL.md, agents/cdc-contract-reviewer.md, sparkforge/integrate/render.py, rules/catalog/routing.yaml, parity.yaml, manifest.json], covers: [AC5], test: {path: tests/test_sync_render.py, name: test_render_e_idempotente}}
---

# STREAMING_CDC — plano

Implementar o extrator e goldens antes da superfície; depois integrar CLI/MCP,
especialista, routing e registros derivados. O commit da wave só sai após os
gates de cobertura e sincronização.
