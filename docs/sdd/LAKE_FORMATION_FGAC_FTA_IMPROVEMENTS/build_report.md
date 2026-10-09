---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS/plan.md
  sha256: "34d468874d788e771981860ed7036b2728dafb77b972c77fb8bebd20398dd419"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t1-red-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_capability_statuses_are_enforced tests/test_lakeformation_fgac_fta_improvements.py::test_source_and_target_are_evaluated_independently tests/test_lakeformation_fgac_fta_improvements.py::test_cross_account_resolution_modes tests/test_lakeformation_fgac_fta_improvements.py::test_hybrid_access_is_governance_aware tests/test_lakeformation_fgac_fta_improvements.py::test_glue4_current_architecture_is_not_migration -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t1-green-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_capability_statuses_are_enforced tests/test_lakeformation_fgac_fta_improvements.py::test_source_and_target_are_evaluated_independently tests/test_lakeformation_fgac_fta_improvements.py::test_cross_account_resolution_modes tests/test_lakeformation_fgac_fta_improvements.py::test_hybrid_access_is_governance_aware tests/test_lakeformation_fgac_fta_improvements.py::test_glue4_current_architecture_is_not_migration -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t2-red-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_catalog_ids_have_semantic_comparisons -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t2-green-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_catalog_ids_have_semantic_comparisons -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t3-red-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_capability_matrix_expands_without_aliasing -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t3-green-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_capability_matrix_expands_without_aliasing -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t4-red-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_improvement_contract_is_documented_and_parity_is_preserved -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-fta-t4-green-20261001 tests/test_lakeformation_fgac_fta_improvements.py::test_improvement_contract_is_documented_and_parity_is_preserved -q", exit: 0}
claims:
  - text: "Capability statuses are enforced per leg: not_supported blocks, read_only blocks writes, and limited/version_dependent require specific verification."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_capability_statuses_are_enforced"
  - text: "Source and target are evaluated independently with their own format, operation, API and capability cell."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_source_and_target_are_evaluated_independently"
  - text: "Glue ETL cross-account can resolve through explicit CatalogId without requiring a resource link, while undeclared routes remain unresolved."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_cross_account_resolution_modes"
  - text: "Hybrid Access separates governance mode from FGAC/FTA table access and does not blanket-block IAMAllowedPrincipals."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_hybrid_access_is_governance_aware"
  - text: "Current Glue 4.0 FGAC DynamicFrame architecture is not migration_required without target runtime or migration intent."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_glue4_current_architecture_is_not_migration"
  - text: "The capability matrix expands conservatively across Glue, EMR EC2 and EMR Serverless without support by analogy."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_capability_matrix_expands_without_aliasing"
  - text: "Catalog routing compares glue.id with ownership and glue.account-id with declared context without aliasing the dimensions."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_catalog_ids_have_semantic_comparisons"
  - text: "Documentation, generated mirrors and CLI/MCP parity preserve the new offline decision contract."
    evidence_ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_improvement_contract_is_documented_and_parity_is_preserved"
change_id: null
---

# LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS — relatório do build

## Resultado

Todas as tarefas T1–T4 foram implementadas com núcleo offline e evidence-first.
O motor preserva o contrato anterior, acrescenta decisões independentes por
perna e permanece fail-closed quando capability, rota ou governança não são
comprovadas.

## Desvios e decisões

- A matriz foi expandida somente para células com fonte e limitação declaradas;
  combinações sem prova continuam `unknown` ou `version_dependent`.
- `capability_verification` fecha apenas `limited`/`version_dependent`; não
  promove `not_supported`, e nenhuma configuração nominal foi tratada como
  prova de capacidade.
- A resolução cross-account deixou de exigir resource link universalmente:
  Glue ETL pode declarar `explicit_catalog_id`; `direct_s3` continua bloqueado
  para tabela governada.
- `access_governance_mode` foi separado de `table_access_model`, permitindo
  Hybrid Access condicionado sem transformar `IAMAllowedPrincipals` em blocker
  universal.
- O teste legado de Glue 4.0 passou a declarar intent de migração quando esse é
  o cenário testado; arquitetura corrente sem target runtime permanece corrente.

## Gates de build

Os gates de mirrors, referências, surface, offline bundle, claims, status
numbers e suíte focada serão registrados após a verificação final. A suíte
completa fica registrada no ship, depois de todas as alterações da feature.
