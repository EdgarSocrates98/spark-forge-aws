---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/design.md
  sha256: "0de3bf42fe37ac1e5011cc5ca14efa8a92c4043296e531305b1d71b673a86e30"
tasks:
  - {id: T1, files: [sparkforge_aws/facts/streaming_integrations.py, fixtures/streaming_integrations], covers: [AC1, AC2, AC3, AC4], test: {path: tests/test_streaming_integrations.py, name: test_goldens_cover_checkpoint_connect_streams_and_openlineage}}
  - {id: T2, files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py], covers: [AC5], test: {path: tests/test_streaming_integrations.py, name: test_cli_and_mcp_envelopes_match}}
  - {id: T3, files: [rules/catalog/streaming-integrations.yaml, tests/test_rules_catalog_reachability.py], covers: [AC1, AC2, AC3, AC4], test: {path: tests/test_rules_catalog_reachability.py, name: test_kind_exigido_tem_extrator_ou_a_regra_declara_blocked_on}}
  - {id: T4, files: [knowledge/streaming-integrations.md, parity.yaml, manifest.json, docs/streaming/prompt-coverage.md], covers: [AC6], test: {path: tests/test_capability_parity.py, name: TestManifestMatchesReality::test_every_phase_zero_tool_appears_in_some_capability}}
  - {id: T5, files: [docs/surface.lock.json, knowledge/offline-manifest.json, docs/superpowers/STATUS.md], covers: [AC6], test: {path: tests/test_host_surface_contracts.py, name: test_full_and_compact_surfaces_have_declared_sizes}}
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — plano

Implementação serializada: extrator e goldens, adapters, rules, conhecimento,
superfícies geradas e gates. Collector live não entra no plano desta wave.
