---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TEMPORAL_EVIDENCE/design.md
  sha256: "d4eb9e8beba61a4ca8bf118bf8c2399fcd77e6885fb2bb1e572c73cca3f5556f"
tasks:
  - id: T1
    files: [tests/test_facts_streaming_temporal.py, sparkforge/facts/streaming_temporal.py]
    covers: [AC1, AC2]
    test: {path: tests/test_facts_streaming_temporal.py, name: test_temporal_pairing_preserves_source_ids_and_skew}
  - id: T2
    files: [tests/test_facts_transport.py, sparkforge/facts/transport.py]
    covers: [AC3]
    test: {path: tests/test_facts_transport.py, name: test_transport_preserves_observed_timestamp}
  - id: T3
    files: [tests/test_streaming_rules.py, rules/catalog/streaming_observability.yaml]
    covers: [AC4]
    test: {path: tests/test_streaming_rules.py, name: test_temporal_rule_requires_paired_observations}
  - id: T4
    files: [sparkforge/facts/streaming_composition.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_analyze_streaming_composition.py]
    covers: [AC6]
    test: {path: tests/test_analyze_streaming_composition.py, name: test_temporal_cli_and_mcp_envelopes_match}
  - id: T5
    files: [fixtures/streaming_temporal, tests/test_fixtures_golden_streaming_temporal.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_streaming_temporal.py, name: test_fixture_goldens}
  - id: T6
    files: [skills/analyze-streaming-composition/SKILL.md, knowledge/streaming-lakehouse-observability.md, docs/streaming/prompt-coverage.md, docs/guia/referencia, docs/surface.lock.json, knowledge/offline-manifest.json]
    covers: [AC7]
    test: {path: tests/test_reference_docs.py, name: test_referencia_em_dia}
---

# STREAMING_TEMPORAL_EVIDENCE — plano

Implementar o núcleo factual antes da superfície: primeiro criar testes que
falhem por ausência do compositor, depois preservar timestamps, adicionar regra,
expor o mesmo modo na CLI/MCP, gerar goldens e só então sincronizar documentação,
surface lock e bundle offline.
