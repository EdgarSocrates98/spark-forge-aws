---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS
phase: define
profile: dev
status: ready
hypothesis:
  claim: "O decision engine pode avaliar cada perna source/target, bloquear capabilities incompatíveis e distinguir rotas de catálogo e modos de governança sem perder o contrato offline."
  prediction: "Casos not_supported, escrita read_only, rota cross-account não resolvida e governança híbrida incompleta deixam de aparecer como consistent; casos Glue ETL com CatalogId explícito, Hybrid Access comprovado e Glue 4.0 corrente permanecem avaliáveis."
  experiment: "Adicionar testes vermelhos para os sete gaps do prompt, implementar o núcleo determinístico, expandir a matriz conservadoramente e executar focused suite, gates de registros e suíte completa."
acceptance:
  - id: AC1
    statement: "Capability not_supported bloqueia, read_only bloqueia escrita, limited exige verificação e version_dependent não fecha sem evidência específica."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_capability_statuses_are_enforced"}
  - id: AC2
    statement: "Source e target produzem decisões independentes com formato e operação próprios, incluindo Parquet read na origem e Iceberg MERGE no destino."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_source_and_target_are_evaluated_independently"}
  - id: AC3
    statement: "Cross-account aceita rota Glue ETL por CatalogId explícito sem exigir resource link, mas mantém rota não declarada unresolved."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_cross_account_resolution_modes"}
  - id: AC4
    statement: "Hybrid Access modela IAMAllowedPrincipals, opt-in, registration e cross-account version sem bloqueio universal."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_hybrid_access_is_governance_aware"}
  - id: AC5
    statement: "Glue 4.0 FGAC DynamicFrame corrente não é migration_required sem target runtime ou intent de migração; migração declarada continua reportada."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_glue4_current_architecture_is_not_migration"}
  - id: AC6
    statement: "Matriz versionada cobre combinações adicionais de Glue 5.1, Glue 6.0, EMR EC2 e EMR Serverless sem promover suporte por analogia."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_capability_matrix_expands_without_aliasing"}
  - id: AC7
    statement: "Routing compara glue.id com ownership e glue.account-id com contexto esperado, aceitando divergência sem colapsar as dimensões quando a semântica está declarada."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_catalog_ids_have_semantic_comparisons"}
  - id: AC8
    statement: "Documentação, skill, agentes, vNext, CLI e MCP preservam o contrato novo e a paridade continua determinística."
    verified_by: {kind: test, ref: "tests/test_lakeformation_fgac_fta_improvements.py::test_improvement_contract_is_documented_and_parity_is_preserved"}
success:
  - id: SC1
    metric: "Acceptance tests AC1–AC8 passando após implementação"
    source: "python -m pytest tests/test_lakeformation_fgac_fta_improvements.py"
  - id: SC2
    metric: "Suítes completas por batches sem falhas após todas as alterações"
    source: "python -m pytest -p no:cacheprovider --basetemp <batch-dir> <batch-glob>"
  - id: SC3
    metric: "Divergências de surface, mirrors, offline bundle, claims e status numbers"
    source: "scripts/sync_skills.py --check, scripts/gen_reference_docs.py --check, scripts/check_surface_lock.py, scripts/verify_offline_bundle.py, scripts/check_vnext_claims.py, scripts/check_status_numbers.py --strict"
out_of_scope:
  - "Nenhuma chamada AWS, alteração de infraestrutura ou concessão automática de IAM/Lake Formation."
  - "Não inferir suporte operacional ausente na documentação nem publicar economia, latência ou tokens sem medição."
  - "Não redesenhar extratores existentes; facts continuam entrando como evidência declarativa."
unknowns: []
case_id: null
change_kinds: [knowledge_doc, agent_or_skill, tool_or_verb, claims]
---

# LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS — requisitos

## Fonte e escopo

Entrada: `prompt_evo_fga_fta_melhoria.md`, revisão do decision engine atual e
documentação oficial AWS Glue/Lake Formation consultada em 2026-10-01.

O escopo fecha enforcement de capability, topologia source/target, resolução
cross-account, Hybrid Access, separação de análise/migração, cobertura da matriz
e semântica de `glue.id`/`glue.account-id`.

## Restrições

- Núcleo offline, evidence-first e fail-closed.
- `unknown`, `limited` e `version_dependent` permanecem lacunas até evidência
  específica; `not_supported` e escrita em `read_only` são bloqueios.
- CLI e MCP continuam usando `analyze_architecture`; nenhuma tool paralela.
- Regenerar espelhos, referência e locks aplicáveis.

## Fontes version-aware

- Resource links: `https://docs.aws.amazon.com/lake-formation/latest/dg/resource-links-about.html`.
- Cross-account prerequisites: `https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-prereqs.html`.
- Hybrid Access: `https://docs.aws.amazon.com/lake-formation/latest/dg/hybrid-access-mode-update.html`.
- Glue FGAC: `https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable.html`.
- Glue 5.1/6.0 migration: `https://docs.aws.amazon.com/glue/latest/dg/migrating-version-51.html` e `https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html`.
