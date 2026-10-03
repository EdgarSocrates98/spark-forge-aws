---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ICEBERG_TEMPORAL/design.md
  sha256: "f395e1c60e1ed8584a5c5ce846e10a7ac7ac1c3708b6efc1b97004342aeb201e"
tasks:
  - id: T1
    files: [tests/test_facts_iceberg_metadata.py, sparkforge/facts/iceberg_metadata.py]
    covers: [AC1]
    test: {path: tests/test_facts_iceberg_metadata.py, name: TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp}
  - id: T2
    files: [tests/test_facts_streaming_composition.py, sparkforge/facts/streaming_iceberg_temporal.py, sparkforge/facts/streaming_composition.py]
    covers: [AC2, AC3]
    test: {path: tests/test_facts_streaming_composition.py, name: test_iceberg_temporal_pairs_progress_and_snapshots}
  - id: T3
    files: [tests/test_streaming_rules.py, rules/catalog/streaming_iceberg.yaml]
    covers: [AC4]
    test: {path: tests/test_streaming_rules.py, name: test_temporal_iceberg_rule_requires_pairs_and_non_append}
  - id: T4
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_streaming_composition.py]
    covers: [AC5]
    test: {path: tests/test_analyze_streaming_composition.py, name: test_iceberg_temporal_cli_and_mcp_envelopes_match}
  - id: T5
    files: [fixtures/streaming_composition, tests/test_fixtures_golden_streaming_composition.py]
    covers: [AC6]
    test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_goldens}
  - id: T6
    files: [skills/analyze-streaming-composition/SKILL.md, knowledge/streaming-lakehouse-observability.md, docs/streaming/prompt-coverage.md, docs/guia/referencia, docs/surface.lock.json, knowledge/offline-manifest.json]
    covers: [AC7]
    test: {path: tests/test_reference_docs.py, name: test_referencia_em_dia}
---

# STREAMING_ICEBERG_TEMPORAL — plano

Implementar em ordem: primeiro snapshot facts, depois compositor temporal e
regra, então adapters/paridade e goldens; por último regenerar documentação,
mirrors, surface lock e bundle offline. O modo legado permanece coberto pelos
goldens existentes.
