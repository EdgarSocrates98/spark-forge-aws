---
sdd: 1
feature: STREAMING_GLUE_RUNTIME_OBSERVATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_RUNTIME_OBSERVATION/plan.md
  sha256: "ea855a466ecdca72f3ccea5123b7c2b547f2c993c6154728b41df30cbd3feb4d"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_runtime_link_matches_literal_job_and_preserves_sources -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_effective_glue_fact_preserves_runtime_capacity_fields tests/test_streaming_glue_runtime_observation.py::test_runtime_link_matches_literal_job_and_preserves_sources -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_fuse_runtime_observation_is_guarded_and_idempotent -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_fuse_runtime_observation_is_guarded_and_idempotent -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_runtime_observation_rules_are_evidence_backed -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_runtime_observation_rules_are_evidence_backed -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_fixture_goldens_cover_consistent_drift_and_unresolved -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_runtime_observation.py::test_fixture_goldens_cover_consistent_drift_and_unresolved tests/test_fixtures_golden_streaming_glue_runtime_observation.py -q", exit: 0}}
  - {id: T5, status: done, red: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_glue_runtime_observation_coverage -q", exit: 1}, green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_glue_runtime_observation_coverage -q", exit: 0}}
claims:
  - text: "A definição efetiva preserva worker_type e worker_count observados sem preencher ausência."
    evidence_ref: "tests/test_streaming_glue_runtime_observation.py::test_effective_glue_fact_preserves_runtime_capacity_fields"
  - text: "fuse correlaciona job e run por nome literal e distingue consistent, divergent e unresolved com source_fact_ids."
    evidence_ref: "tests/test_streaming_glue_runtime_observation.py::test_runtime_link_reports_drift_and_unresolved_without_inference"
  - text: "O catálogo julga drift e blind spot com evidência não vazia."
    evidence_ref: "tests/test_streaming_glue_runtime_observation.py::test_runtime_observation_rules_are_evidence_backed"
change_id: null
---

# STREAMING_GLUE_RUNTIME_OBSERVATION — relatório do build

O build adiciona composição offline entre definição efetiva Glue Streaming e
facts terminais de `glue.job_run`. Reutiliza `fuse`, o analyzer/collector de
runs e a superfície existente; não cria verbo CLI nem ferramenta MCP.

## Validação

Os testes do contrato passaram (`9 passed`), os goldens e o gate de domínio
passaram (`5 passed`) e a cobertura documental passou. O corpus inclui
consistent, drift e ausência de run; os cenários com `glue.job_run` preservam
explicitamente o `spark.timeout.unresolved` já produzido pelo compositor. A
suíte completa não foi executada nesta fase.

## Limites

O vínculo exige nome literal, não consulta AWS e não prova latência, throughput,
custo, saúde, capacidade suficiente ou resultado funcional. Duração e DPU são
observações de run, não latência de evento. Source/sink e validação funcional
continuam fora deste contrato.
