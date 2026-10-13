---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_TRANSPORT_EVALUATION/design.md
  sha256: "46b34d1b9fa22bc78acfcaaaf2a9806275439e4dbf7f92fb4df227f124380df8"
tasks:
  - id: T1
    files: [tests/test_facts_streaming_slo.py, sparkforge_aws/facts/streaming_slo.py, sparkforge_aws/facts/transport.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_streaming_slo.py, name: test_evaluates_transport_slo_by_declared_identity}
  - id: T2
    files: [sparkforge_aws/facts/streaming_composition.py, sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/tools.py, tests/test_analyze_streaming_composition.py]
    covers: [AC4]
    test: {path: tests/test_analyze_streaming_composition.py, name: test_transport_slo_cli_and_mcp_envelopes_match}
  - id: T3
    files: [fixtures/streaming_composition, tests/test_fixtures_golden_streaming_composition.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_streaming_composition.py, name: test_fixture_goldens}
  - id: T4
    files: [skills/analyze-streaming-composition/SKILL.md, knowledge/transport-diagnostics.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_transport_slo_coverage_mentions_transport_key}
  - id: T5
    files: [docs/surface.lock.json, knowledge/offline-manifest.json, manifest.json]
    covers: [AC6]
    test: {path: tests/test_surface_lock.py, name: TestOLockBateComAMedida::test_the_tool_catalogue_matches}
---

# STREAMING_SLO_TRANSPORT_EVALUATION — plano

Executar em ordem T1–T5. T1 escreve testes vermelhos para identidade,
comparadores, unidade, timestamp e cobertura de Kafka/Kinesis. T2 liga o
parâmetro existente ao core único. T3 cria goldens met/violated/unresolved. T4
documenta o caminho econômico e seus limites. T5 regenera surface/manifests e
fecha os gates. Suíte completa continua fora desta frente.
