---
sdd: 1
feature: ORCHESTRATION_CONTROL_PLANE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/ORCHESTRATION_CONTROL_PLANE/explore.md
  sha256: "450f758cac93a2b035a9b5c106618f432944d6e535d126e93cfff2e1c6721e46"
hypothesis:
  claim: "Um mapa normalizado de workflows expõe riscos de retries, backfill, concurrency, sensores, idempotência e dependências entre Airflow, Dagster, Step Functions e Control-M."
  prediction: "Workflows declarados preservam a plataforma de origem e campos operacionais; referências ausentes ou propriedades não declaradas viram unresolved."
  experiment: "Analisar fixture multi-orchestrator por CLI/MCP e conferir saída canônica."
acceptance:
  - id: AC1
    statement: "O contrato normaliza orquestradores e workflows sem inferir idempotência, retries ou dependências."
    verified_by: {kind: test, ref: "tests/test_orchestration.py::test_orchestration_normalizes_reliability_controls"}
  - id: AC2
    statement: "A análise retorna unresolved para dependência ausente e propriedade operacional omitida."
    verified_by: {kind: test, ref: "tests/test_orchestration.py::test_orchestration_preserves_unresolved_controls"}
  - id: AC3
    statement: "CLI e MCP compartilham o mesmo relatório de orchestration control plane."
    verified_by: {kind: command, ref: "python -m sparkforge_aws.adapters.cli analyze orchestration --path fixtures/orchestration/control-plane.yaml"}
success:
  - id: SC1
    metric: "Cada workflow mantém orchestrator, idempotency, retry, backfill, sensor e concurrency declarados"
    source: "relatório normalizado"
out_of_scope:
  - "Disparar DAG, job, state machine ou comando Control-M."
  - "Inferir retries ou idempotência por nome de tarefa."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Registrar nova tool e referência gerada."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc]
---

# ORCHESTRATION_CONTROL_PLANE — requisitos

O inventário deve distinguir declaração, observação e ausência. Configuração
operacional sem fonte não é recomendação; é unresolved.
