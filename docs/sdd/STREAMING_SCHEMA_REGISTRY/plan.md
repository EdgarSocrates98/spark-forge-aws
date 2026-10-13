---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY/design.md
  sha256: "03cd0de65501ad9b4e03e7ed5fe2de85b01a9e598996522ef5a8f7d0d81954d5"
tasks:
  - {id: T1, files: [sparkforge_aws/facts/schema_registry.py, tests/test_facts_schema_registry.py], covers: [AC1], test: {path: tests/test_facts_schema_registry.py, name: test_schema_registry_extracts_diff_and_unresolved_policy}}
  - {id: T2, files: [fixtures/schema_registry, rules/catalog/schema_registry.yaml, scripts/regen_schema_registry_fixtures.py, tests/test_fixtures_golden_schema_registry.py, tests/test_schema_registry_rules.py], covers: [AC2, AC3], test: {path: tests/test_fixtures_golden_schema_registry.py, name: test_schema_registry_fixture_goldens}}
  - {id: T3, files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, tests/test_analyze_schema_registry.py], covers: [AC4], test: {path: tests/test_analyze_schema_registry.py, name: test_cli_and_mcp_schema_registry_envelopes_match}}
  - {id: T4, files: [skills/review-cdc-replication/SKILL.md, rules/catalog/routing.yaml, parity.yaml, manifest.json], covers: [AC5], test: {path: tests/test_sync_render.py, name: test_render_e_idempotente}}
---

# STREAMING_SCHEMA_REGISTRY — plano
