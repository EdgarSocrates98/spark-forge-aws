---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/design.md
  sha256: "41028b116c8d330beee46e06a2a04c4fcbe4dd76608f85d72e8e78812aae5aec"
tasks:
  - {id: T1, files: [tests/test_facts_transport.py, sparkforge_aws/facts/transport.py], covers: [AC1, AC2, AC3], test: {path: tests/test_facts_transport.py, name: test_kafka_dump_emits_topic_partition_group_and_lag_facts}}
  - {id: T2, files: [fixtures/transport, tests/test_fixtures_golden_transport.py], covers: [AC5], test: {path: tests/test_fixtures_golden_transport.py, name: test_transport_fixture_corpus_is_complete}}
  - {id: T3, files: [sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, tests/test_analyze_transport.py], covers: [AC4], test: {path: tests/test_analyze_transport.py, name: test_cli_and_mcp_transport_envelopes_match}}
  - {id: T4, files: [knowledge/transport-diagnostics.md, knowledge/INDEX.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, manifest.json], covers: [AC5], test: {path: tests/test_fixtures_golden_transport.py, name: test_transport_fixture_corpus_is_complete}}
  - {id: T5, files: [docs/surface.lock.json, docs/guia/referencia], covers: [AC6], test: {path: tests/test_reference_docs.py, name: test_referencia_em_dia}}
---

# STREAMING_TRANSPORT_DIAGNOSTICS — plano

Implementar T1 em red/green, criar corpus antes do adapter, e só então publicar
CLI/MCP. Recalcular referências, parity e locks no fechamento.
