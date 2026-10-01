---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/design.md
  sha256: "5a56d7f630428b9c03763a234a30e6fd79a67ff213fe0049b9893c14c7ac6cf5"
tasks:
  - id: T1
    files: [knowledge/lakeformation/capability-matrix.yaml, sparkforge/lakeformation/capabilities.py, tests/test_lakeformation_architecture.py]
    covers: [AC3, AC4, AC5]
    test: {path: tests/test_lakeformation_architecture.py, name: test_capability_matrix_is_source_backed}
  - id: T2
    files: [sparkforge/lakeformation/catalog_routing.py, sparkforge/lakeformation/architecture.py, tests/test_lakeformation_architecture.py]
    covers: [AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC10]
    test: {path: tests/test_lakeformation_architecture.py, name: test_routing_preserves_account_ownership_dimensions}
  - id: T3
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_lakeformation_architecture.py, tests/test_adapters_mcp_compact.py, tests/test_host_surface_contracts.py, tests/test_fixtures_golden_mcp_parity.py, tests/test_harness_boundary.py, fixtures/knowledge_drift/lf_consideracoes/expected/result.json]
    covers: [AC11]
    test: {path: tests/test_lakeformation_architecture.py, name: test_cli_and_mcp_architecture_parity}
  - id: T4
    files: [knowledge/lakeformation/architecture.md, skills/lakeformation-architecture/SKILL.md, sparkforge/integrate/render.py, agents/sf-lake-formation-specialist.md, agents/sf-runtime-specialist.md, docs/guia/usos/lake-formation-e-acesso.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CAPABILITY-MATRIX.md, docs/vnext/KNOWLEDGE-MAP.md, docs/claims.lock.json, docs/surface.lock.json, manifest.json, tests/test_sync_render.py, tests/test_lakeformation_architecture.py]
    covers: [AC12]
    test: {path: tests/test_lakeformation_architecture.py, name: test_architecture_docs_and_vnext_are_anchored}
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — plano

## T1 — matriz de capacidades version-aware

Teste primeiro, em \`tests/test_lakeformation_architecture.py\`:

\`\`\`python
from sparkforge.lakeformation.capabilities import capability, load_matrix


def test_capability_matrix_is_source_backed():
    matrix = load_matrix()
    assert {"glue", "emr_ec2", "emr_serverless"} <= set(matrix["engines"])
    for row in matrix["capabilities"]:
        assert row["status"] in {
            "supported", "limited", "read_only", "version_dependent",
            "not_supported", "unknown",
        }
        if row["status"] != "unknown":
            assert row["source"] and row["last_verified"] and row["limitations"]
    assert capability("glue", "5.1", "fgac", "iceberg", "merge")["status"] in {
        "supported", "limited", "version_dependent"
    }
    assert capability("emr_ec2", "7.8.0", "fta", "iceberg", "read")["status"] == "supported"

\`\`\`

Rodar e ver falhar com \`ModuleNotFoundError\` da unidade nova:

\`\`\`bash
python -m pytest tests/test_lakeformation_architecture.py::test_capability_matrix_is_source_backed -q
\`\`\`

Código mínimo: criar \`knowledge/lakeformation/capability-matrix.yaml\` com fontes oficiais verificadas em 2026-09-30, células para Glue 4.0/5.0/5.1, EMR EC2 6.15/7.8/7.10/7.12 e EMR Serverless 7.2/7.9/7.12, e \`sparkforge/lakeformation/capabilities.py\` com loader \`safe_knowledge_file\`, vocabulário fechado, \`load_matrix()\`, \`capability()\` e unresolved para engine/release ausente.

Rodar o mesmo teste até exit 0. Gates vizinhos: knowledge offline bundle, sources lock e \`tests/test_lakeformation_architecture.py\`. Commit: \`feat(lakeformation): add version-aware capability matrix\`.

## T2 — routing, decisão e preflight

Testes primeiro, em \`tests/test_lakeformation_architecture.py\`, cobrindo os node ids AC1–AC10. O primeiro comando deve falhar com \`ModuleNotFoundError\` de \`catalog_routing\` ou \`architecture\`; cada cenário deve afirmar o nome do estado, camada e \`required_verification\`, não apenas um booleano.

\`\`\`bash
python -m pytest \
  tests/test_lakeformation_architecture.py::test_routing_preserves_account_ownership_dimensions \
  tests/test_lakeformation_architecture.py::test_routing_does_not_alias_glue_id_and_account_id \
  tests/test_lakeformation_architecture.py::test_glue4_dynamicframe_to_glue5_fgac_is_migration \
  tests/test_lakeformation_architecture.py::test_glue_access_model_is_version_and_operation_aware \
  tests/test_lakeformation_architecture.py::test_emr_release_capabilities_are_version_aware \
  tests/test_lakeformation_architecture.py::test_read_and_write_authorization_are_separate \
  tests/test_lakeformation_architecture.py::test_credential_vending_preflight_is_layered \
  tests/test_lakeformation_architecture.py::test_cross_account_governance_requires_independent_evidence \
  tests/test_lakeformation_architecture.py::test_golden_path_glue51_cross_account_iceberg \
  tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed -q
\`\`\`

Código mínimo:

1. \`sparkforge/lakeformation/catalog_routing.py\`: validar e normalizar apenas shape, preservar seis account dimensions, comparar \`glue_id\` e \`glue_account_id\` separadamente, e retornar \`unresolved\` para ambiguidade/ausência.
2. \`sparkforge/lakeformation/architecture.py\`: chamar \`capability()\`, classificar Glue/EMR/Serverless, decidir FGAC/FTA/migration_required, separar read/write, verificar \`GetDataAccess\`, application integration, filesystem, LF grants, RAM, links, registration e IAMAllowedPrincipals; nunca fabricar evidence.
3. O output deve conter \`status\`, \`decision\`, \`routing\`, \`checks\`, \`observed\`, \`inferred\`, \`required_verification\`, \`risks\` e \`rollback\`.

Rodar os mesmos testes até exit 0. Gates vizinhos: \`ruff\` nos três módulos e teste de imports offline. Commit: \`feat(lakeformation): add governed access architecture decision engine\`.

## T3 — superfície CLI/MCP

Teste primeiro:

\`\`\`bash
python -m pytest tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity -q
\`\`\`

O vermelho esperado é \`AttributeError\`/\`KeyError\` porque o adapter ainda não expõe o verbo/tool.

Código mínimo:

- \`sparkforge/adapters/_core.py\`: \`lakeformation_architect(payload)\` delega somente ao módulo puro e mantém o envelope existente.
- \`sparkforge/adapters/cli.py\`: registrar \`sparkforge lakeformation architect --input <json>\` e serializar o mesmo payload.
- \`sparkforge/adapters/tools.py\`: registrar \`sparkforge_lakeformation_architect\`, schema do payload e handler sem leitura livre de disco ou chamada AWS.
- Teste chama a função core e os dois adapters sobre o mesmo fixture declarativo e compara \`status\`, \`decision\`, \`routing\` e \`checks\`.

Rodar até exit 0. Gates vizinhos: \`python scripts/gen_reference_docs.py\`, \`python -m pytest tests/test_reference_docs.py tests/test_adapters_cli.py tests/test_adapters_tools.py -q\`, \`python scripts/check_surface_lock.py --update\` apenas se o crescimento estiver declarado no commit. Commit: \`feat(lakeformation): expose architecture analysis through cli and mcp\`.

## T4 — conhecimento, skill, agents e VNX

Teste primeiro:

\`\`\`bash
python -m pytest tests/test_lakeformation_architecture.py::test_architecture_docs_and_vnext_are_anchored -q
\`\`\`

O vermelho esperado é \`AssertionError\` porque o skill, fontes oficiais ou referências VNX ainda não contêm o contrato novo.

Código/documentação mínima:

- Criar \`knowledge/lakeformation/architecture.md\` apontando para a matriz, descrevendo progressive disclosure, camadas de autorização e limites.
- Criar \`skills/lakeformation-architecture/SKILL.md\` com protocolo evidence-first e não-faz; atualizar \`agents/sf-lake-formation-specialist.md\` e \`agents/sf-runtime-specialist.md\`; sincronizar \`.agents\`, \`.claude\` e \`.github\` com \`python scripts/sync_skills.py\`.
- Atualizar os três documentos VNX sem claims de economia/performance não medidos; rodar \`python scripts/check_vnext_claims.py --seed\` somente para registrar claims novas e classificar cada uma com evidência.
- Atualizar \`docs/guia/usos/lake-formation-e-acesso.md\` e gerar referências de CLI/tool.

Rodar o teste até exit 0. Gates vizinhos: \`python scripts/sync_skills.py --check\`, \`python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q\`, \`python scripts/check_vnext_claims.py\`, \`python -m pytest tests/test_vnext_claims.py tests/test_installed_provenance.py -q\`, \`python scripts/refresh_knowledge.py --update --offline\`, \`python scripts/verify_offline_bundle.py\`, \`python scripts/gen_reference_docs.py\` e \`python -m pytest tests/test_reference_docs.py -q\`. Commit: \`docs(lakeformation): publish governed architecture workflow and vnext map\`.

## Autorrevisão do plano

- Cada AC aparece em \`covers\`.
- Cada arquivo do manifesto aparece em uma tarefa.
- Nenhuma tarefa depende de valor inventado; a matriz expõe \`unknown\`.
- Cada tarefa tem teste nomeado e commit próprio.
