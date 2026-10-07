---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_CROSS_ARTIFACT/plan.md
  sha256: "12b29e6f4381eeac69140523d5dd03270c652dec47b82407f522970dcbeff7b5"
tasks:
  - {id: T1, status: done, red: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py -q", exit: 0}}
  - {id: T2, status: done, red: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_fuse_cross_artifact_is_guarded_and_idempotent -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_fuse_cross_artifact_is_guarded_and_idempotent -q", exit: 0}}
  - {id: T3, status: done, red: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_cross_artifact_rules_are_evidence_backed -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_cross_artifact_rules_are_evidence_backed -q", exit: 0}}
  - {id: T4, status: done, red: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_fixture_goldens_cover_match_drift_and_unresolved -q", exit: 1}, green: {command: "python -m pytest tests/test_streaming_glue_cross_artifact.py::test_fixture_goldens_cover_match_drift_and_unresolved -q", exit: 0}}
  - {id: T5, status: done, red: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_glue_cross_artifact_coverage -q", exit: 1}, green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_glue_cross_artifact_coverage -q", exit: 0}}
claims:
  - text: "Glue Streaming efetivo e Terraform são correlacionados somente por aws_glue_job.name literal e único."
    evidence_ref: "tests/test_streaming_glue_cross_artifact.py::test_matches_effective_glue_job_to_terraform_resource"
  - text: "Drift e lacuna de evidência permanecem estados distintos e chegam ao catálogo com source_fact_ids."
    evidence_ref: "tests/test_streaming_glue_cross_artifact.py::test_fixture_goldens_cover_match_drift_and_unresolved"
change_id: null
---

# STREAMING_GLUE_CROSS_ARTIFACT — relatório do build

O build adiciona composição offline entre o job Glue Streaming efetivo e o
Terraform. O compositor existente `fuse` foi reutilizado; nenhuma ferramenta
MCP ou verbo CLI novo foi criado.

## Validação

Os testes específicos do contrato, integração de `fuse`, catálogo e goldens
passaram: `12 passed`. O lote de facts/fusão e reachability passou com
`894 passed`; docs, mirrors e renderização passaram com `156 passed`. A
cobertura inclui caso consistente, drift e identidade/valor não resolvido. A
suíte completa não foi executada nesta fase.
