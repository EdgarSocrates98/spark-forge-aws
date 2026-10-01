---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/plan.md
  sha256: "7743bf37207287a7398e814250d18a2d41bcb932cbfdddc92ecd6358a04218f4"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t1-red-20261001 tests/test_lakeformation_architecture.py::test_capability_matrix_is_source_backed -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t1-green-20261001 tests/test_lakeformation_architecture.py::test_capability_matrix_is_source_backed -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t2-red-20261001 tests/test_lakeformation_architecture.py::test_routing_preserves_account_ownership_dimensions tests/test_lakeformation_architecture.py::test_routing_does_not_alias_glue_id_and_account_id tests/test_lakeformation_architecture.py::test_glue4_dynamicframe_to_glue5_fgac_is_migration tests/test_lakeformation_architecture.py::test_glue_access_model_is_version_and_operation_aware tests/test_lakeformation_architecture.py::test_emr_release_capabilities_are_version_aware tests/test_lakeformation_architecture.py::test_read_and_write_authorization_are_separate tests/test_lakeformation_architecture.py::test_credential_vending_preflight_is_layered tests/test_lakeformation_architecture.py::test_cross_account_governance_requires_independent_evidence tests/test_lakeformation_architecture.py::test_golden_path_glue51_cross_account_iceberg tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t2-green3-20261001 tests/test_lakeformation_architecture.py::test_routing_preserves_account_ownership_dimensions tests/test_lakeformation_architecture.py::test_routing_does_not_alias_glue_id_and_account_id tests/test_lakeformation_architecture.py::test_glue4_dynamicframe_to_glue5_fgac_is_migration tests/test_lakeformation_architecture.py::test_glue_access_model_is_version_and_operation_aware tests/test_lakeformation_architecture.py::test_emr_release_capabilities_are_version_aware tests/test_lakeformation_architecture.py::test_read_and_write_authorization_are_separate tests/test_lakeformation_architecture.py::test_credential_vending_preflight_is_layered tests/test_lakeformation_architecture.py::test_cross_account_governance_requires_independent_evidence tests/test_lakeformation_architecture.py::test_golden_path_glue51_cross_account_iceberg tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t3-red-20261001 tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t3-green2-20261001 tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity tests/test_adapters_tools.py::TestToolSurface::test_the_full_tool_surface_is_declared tests/test_adapters_tools.py::TestRealOutputValidatesAgainstItsOwnSchema::test_real_output_matches_declared_schema[sparkforge_lakeformation_architect] -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t4-red-20261001 tests/test_lakeformation_architecture.py::test_architecture_docs_and_vnext_are_anchored -q", exit: 1}
    green: {command: "python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-t4-green2-20261001 tests/test_lakeformation_architecture.py::test_architecture_docs_and_vnext_are_anchored -q", exit: 0}
claims:
  - text: "A matriz de capacidades foi carregada com fonte, estado fechado e fallback unresolved."
    evidence_ref: "tests/test_lakeformation_architecture.py::test_capability_matrix_is_source_backed"
  - text: "Routing preserva ownership e não aliasa glue.id com glue.account-id."
    evidence_ref: "tests/test_lakeformation_architecture.py::test_routing_does_not_alias_glue_id_and_account_id"
  - text: "A decisão arquitetural separa FGAC/FTA, read/write, credential vending e cross-account."
    evidence_ref: "tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed"
  - text: "CLI e MCP retornam o mesmo contrato no mesmo input declarativo."
    evidence_ref: "tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity"
  - text: "Knowledge, skill, coordenadores, referências e VNX estão ancorados sem claim de ganho não medido."
    evidence_ref: "tests/test_lakeformation_architecture.py::test_architecture_docs_and_vnext_are_anchored"
change_id: null
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — relatório do build

## Resultado

Todas as tarefas T1–T4 foram concluídas. Os testes acceptance passaram após
vermelhos observados pelo motivo correto. O implementation é offline: não chama
AWS, não altera permissões e não promete custo, latência, workers ou tokens.

## Desvios do plano

- O `change_kinds` inicial continha `fixture_corpus`, mas nenhum corpus de
  fixtures foi necessário para o contrato declarativo; a entrada foi removida
  antes do stamp do design.
- A nova decisão de despacho exigiu registrar `lakeformation-architecture` em
  `sparkforge/integrate/render.py`, `tests/test_sync_render.py`, `manifest.json`
  e nos registros gerados de superfície e referência.
- O plan foi ampliado para declarar `docs/surface.lock.json`, porque o novo MCP
  tool mediu crescimento da superfície; o lock registra 115 tools, 52 skills e
  58 documentos knowledge.
- A matriz não preenche Glue 6.x por extrapolação. Células sem fonte permanecem
  `unknown`/`unresolved`, conforme define e design.
- As provas VNX divergentes foram re-medidas pelo verificador e atualizadas nos
  valores de `docs/claims.lock.json`; entradas `REMOVIDA` foram preservadas.

## Gates e revisões

- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/refresh_knowledge.py --update --offline` — exit 0; 276 fontes,
  261 móveis e 15 fixas.
- `python scripts/verify_offline_bundle.py` — exit 0; 57 fontes verificadas.
- `python scripts/gen_reference_docs.py` — exit 0; 242 páginas, 8 regravadas.
- `python scripts/check_surface_lock.py` — exit 0 após atualização declarada.
- `python scripts/check_vnext_claims.py` — exit 0; 0 divergências.
- `python -m pytest tests/test_vnext_claims.py tests/test_installed_provenance.py -q`
  — exit 0; 147 passed, 5 skipped.
- `python -m pytest tests/test_sync_render.py tests/test_docs_coverage.py
  tests/test_agents_parity.py tests/test_agent_coverage.py -q` — exit 0; 203
  passed.
- `python -m pytest tests/test_reference_docs.py -q` — exit 0; 5 passed.
- `ruff check` nos módulos e testes tocados — exit 0.

## Revisão final

A revisão final conferiu o diff da feature contra define/design: cada AC tem
teste, cada tarefa tem vermelho e verde, os adapters mantêm paridade, os
espelhos são derivados dos agentes fonte e os registros de surface, claims,
knowledge e referência foram atualizados. Não há mutação AWS nem ganho de
desempenho a medir nesta feature.

## Pendência de integração

A suíte completa será executada em lotes somente no encerramento da feature,
antes do commit de ship/push. Até essa execução, o relatório permanece
`ready`, não `done`.
