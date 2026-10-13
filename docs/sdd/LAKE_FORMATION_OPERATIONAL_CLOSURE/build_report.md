---
sdd: 1
feature: LAKE_FORMATION_OPERATIONAL_CLOSURE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_OPERATIONAL_CLOSURE/plan.md
  sha256: "21a0410891127e6b5dc7e3133a14e9e2a0aa450f713cfd8692fbc087382d87d6"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t1-red-20261001 tests/test_lakeformation_operational_closure.py::test_review_composes_code_iac_and_late_configuration tests/test_lakeformation_operational_closure.py::test_review_explains_access_and_root_cause_layers -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t1-green3-20261001 tests/test_lakeformation_operational_closure.py::test_review_composes_code_iac_and_late_configuration tests/test_lakeformation_operational_closure.py::test_review_explains_access_and_root_cause_layers -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t2-red2-20261001 tests/test_lakeformation_operational_closure.py::test_review_builds_version_aware_migration_report tests/test_lakeformation_operational_closure.py::test_matrix_closure_keeps_format_and_source_boundaries -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t2-green-20261001 tests/test_lakeformation_operational_closure.py::test_review_builds_version_aware_migration_report tests/test_lakeformation_operational_closure.py::test_matrix_closure_keeps_format_and_source_boundaries -q", exit: 0}
  - id: T3
    status: skipped
  - id: T4
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t4-red-20261001 tests/test_lakeformation_operational_closure.py::test_cli_and_mcp_operational_review_parity tests/test_lakeformation_operational_closure.py::test_operational_closure_docs_and_vnx_are_anchored -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-op-t4-green6-20261001 tests/test_lakeformation_operational_closure.py::test_cli_and_mcp_operational_review_parity tests/test_lakeformation_operational_closure.py::test_operational_closure_docs_and_vnx_are_anchored -q", exit: 0}
claims:
  - text: "A revisão compõe fatos de PySpark, Spark config e Terraform e mantém required_verification para evidência ausente."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_review_composes_code_iac_and_late_configuration"
  - text: "Access explain separa metadata, dados e credential vending e classifica camadas de erro e root cause."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_review_explains_access_and_root_cause_layers"
  - text: "Migration report preserva mudanças breaking, semantic, security, performance e cost sem números inventados."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_review_builds_version_aware_migration_report"
  - text: "Preflight e cross-review mantêm least privilege, IAMAllowedPrincipals e camadas de especialista."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_review_preflight_is_least_privilege_and_cross_reviewed"
  - text: "Performance/FinOps publica impactos condicionais e medidas requeridas quando benchmark ou DPUSeconds ausentes."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_review_preserves_evidence_and_progressive_disclosure"
  - text: "Capability matrix mantém limites version-aware por engine, release, formato e operação."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_matrix_closure_keeps_format_and_source_boundaries"
  - text: "CLI e MCP devolvem o mesmo payload operacional sem nova tool paralela."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_cli_and_mcp_operational_review_parity"
  - text: "Knowledge, runbook, skill, agentes e VNX carregam as âncoras operacionais exigidas."
    evidence_ref: "tests/test_lakeformation_operational_closure.py::test_operational_closure_docs_and_vnx_are_anchored"
change_id: null
---

# LAKE_FORMATION_OPERATIONAL_CLOSURE — relatório do build

## Desvios e decisões

- T3 foi `skipped` como tarefa de implementação: os contratos de `preflight`,
  `performance_finops` e `cross_review` já foram entregues em T1 e os testes de
  AC4/AC5 passaram antes de T3. Os testes são guardas explícitos contra regressão;
  não há vermelho próprio honesto para registrar nessa tarefa.
- T2 preservou `version_dependent` para Glue 5.1 FGAC Iceberg MERGE porque a
  documentação do runtime não fecha sozinha operação, permissões, routing e
  credential path. A divergência Hudi/Delta FTA também permanece version-dependent.
- A correção do teste legado que esperava `version_dependent` foi registrada em
  commit separado; nenhuma célula foi promovida por analogia entre releases.
- T4 atualizou espelhos gerados, referência de tool, surface lock, claims e
  knowledge lock. Crescimentos de superfície foram medidos e declarados; nenhuma
  economia ou ganho de performance foi afirmado.

## Gates de build

`ruff`, suíte focada de Lake Formation, `sync_skills --check`, referência gerada,
`check_surface_lock`, `verify_offline_bundle`, `check_status_numbers --strict` e
auditoria de claims foram executados. A suíte completa fica registrada no ship,
depois de todas as alterações da feature.
