---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/plan.md
  sha256: "6870b671f21b8fa19310fee7a700a361f1ed80fbcd092cfc75fa109646ca1b3e"
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
- A primeira suíte completa encontrou expectativas históricas de 114 tools em
  `tests/test_adapters_mcp_compact.py` e `tests/test_host_surface_contracts.py`;
  ambas foram atualizadas para o contador declarado de 115 (114 no HTTP full).
- O lote de goldens encontrou duas referências derivadas da superfície nova:
  `tests/test_fixtures_golden_mcp_parity.py` recebeu a allowlist da tool e o
  golden de knowledge drift foi regenerado pelo flag oficial, sem edição manual.
- A suíte completa expôs fragilidade de um teste de fronteira que injetava
  código no checkout real e falhava ao restaurar esse arquivo no Windows; o
  cenário foi isolado em runtime temporário, mantendo a mesma prova do
  detector e eliminando contaminação entre testes.
- A expansão da skill alterou bytes da superfície; `docs/surface.lock.json` foi
  reemitido pelo medidor e conferido sem divergência.

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
- `python -m pytest -p no:cacheprovider --basetemp E:\\pytest-lf-surface-fix-20261001
  tests/test_adapters_mcp_compact.py tests/test_host_surface_contracts.py -q` —
  exit 0; 14 passed.
- `SPARKFORGE_REGEN_DRIFT=1 python -m pytest tests/test_fixtures_golden_knowledge_drift.py -q`
  — exit 0; 11 passed.
- `python -m pytest tests/test_fixtures_golden_mcp_parity.py -q` — exit 0; 13
  passed.
- `python -m pytest tests/test_harness_boundary.py::TestADeteccaoEnxergaImportRelativo::test_violacao_relativa_injetada_num_modulo_real_fica_vermelha tests/test_integrate.py::test_scope_user_nao_escreve_no_repo_pela_cli tests/test_surface_lock.py::TestOLockBateComAMedida -q` — exit 0; 9 passed.

## Revisão final

A revisão final conferiu o diff da feature contra define/design: cada AC tem
teste, cada tarefa tem vermelho e verde, os adapters mantêm paridade, os
espelhos são derivados dos agentes fonte e os registros de surface, claims,
knowledge e referência foram atualizados. Não há mutação AWS nem ganho de
desempenho a medir nesta feature.

## Suíte completa

Executada em nove lotes disjuntos, um por vez, com `-p no:cacheprovider` e
`--basetemp` externo, conforme `tests/test_suite_batches.py`:

- `a-c`: 2506 passed, 2 skipped.
- `d-e`: 559 passed.
- `f-sem-golden`: 1929 passed, 2 skipped.
- `goldens-1`: 1452 passed, 4 skipped.
- `goldens-2`: 579 passed.
- `goldens-3`: 371 passed.
- `goldens-4`: 305 passed.
- `goldens-5`: 523 passed.
- `g-z`: 5451 passed, 6 skipped.

Total final: **13689 coletados, 13675 passed, 14 skipped**. Uma primeira
execução encontrou e corrigiu expectativas de superfície, goldens derivados,
contadores correntes e fragilidade Windows no teste de fronteira; os lotes
afetados foram repetidos verdes após cada correção.
