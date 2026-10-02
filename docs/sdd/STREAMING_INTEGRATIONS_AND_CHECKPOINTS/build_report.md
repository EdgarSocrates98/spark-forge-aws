---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/plan.md
  sha256: "a1fcfa4acd3b4d46c81ec189538543952762b08c98842ec8a80cae058b1aa9c3"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_streaming_integrations.py::test_cli_and_mcp_envelopes_match -q", exit: 1}, green: {command: "python -m pytest tests/test_adapters_tools.py tests/test_adapters_mcp_compact.py -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q", exit: 1}, green: {command: "python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python -m pytest tests/test_capability_parity.py -q", exit: 1}, green: {command: "python scripts/check_surface_lock.py; python scripts/verify_offline_bundle.py --check", exit: 0}}
  - {id: T5, status: done, red: {command: "python -m sparkforge.adapters.cli sdd check --repo . --feature STREAMING_INTEGRATIONS_AND_CHECKPOINTS", exit: 1}, green: {command: "python -m sparkforge.adapters.cli sdd check --repo . --feature STREAMING_INTEGRATIONS_AND_CHECKPOINTS", exit: 0}}
claims:
  - text: "Contrato completo produz facts para checkpoint, Kafka Connect, Kafka Streams e OpenLineage."
    evidence_ref: "tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage"
  - text: "Contrato incompleto produz quatro rules com evidence e fact_id distintos."
    evidence_ref: "fixtures/streaming_integrations/incomplete/expected/findings.json"
change_id: null
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — relatório do build

O build mantém o core offline. A coleta live e a validação funcional são
limitações nomeadas, não capabilities silenciosamente omitidas.
