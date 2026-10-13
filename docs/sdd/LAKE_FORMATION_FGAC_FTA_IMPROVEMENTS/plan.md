---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS/design.md
  sha256: "9403467aad378839d560f0abddaf07b7bb341d6409b7d9c27708c45efea7fc10"
tasks:
  - id: T1
    files: [tests/test_lakeformation_fgac_fta_improvements.py, sparkforge_aws/lakeformation/architecture.py]
    covers: [AC1, AC2, AC3, AC4, AC5]
    test: {path: tests/test_lakeformation_fgac_fta_improvements.py, name: test_capability_statuses_are_enforced}
  - id: T2
    files: [tests/test_lakeformation_fgac_fta_improvements.py, sparkforge_aws/lakeformation/catalog_routing.py]
    covers: [AC2, AC3, AC7]
    test: {path: tests/test_lakeformation_fgac_fta_improvements.py, name: test_catalog_ids_have_semantic_comparisons}
  - id: T3
    files: [tests/test_lakeformation_fgac_fta_improvements.py, knowledge/lakeformation/capability-matrix.yaml]
    covers: [AC6]
    test: {path: tests/test_lakeformation_fgac_fta_improvements.py, name: test_capability_matrix_expands_without_aliasing}
  - id: T4
    files: [knowledge/lakeformation/fgac-fta-improvements.md, skills/lakeformation-architecture/SKILL.md, agents/sf-lake-formation-specialist.md, agents/sf-runtime-specialist.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CAPABILITY-MATRIX.md, docs/vnext/KNOWLEDGE-MAP.md, tests/test_lakeformation_fgac_fta_improvements.py]
    covers: [AC8]
    test: {path: tests/test_lakeformation_fgac_fta_improvements.py, name: test_improvement_contract_is_documented_and_parity_is_preserved}
---

# LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS — plano

## T1 — enforcement e pernas source/target

Escrever testes vermelhos cobrindo status capability, source Parquet/read,
target Iceberg/MERGE, CatalogId explícito, Hybrid Access e Glue 4.0 corrente.
Implementar helpers puros em `architecture.py`, preservando chaves existentes e
sem chamar AWS. TDD: red, green, focused suite; commit de código.

## T2 — routing semântico

Adicionar comparações nomeadas em `catalog_routing.py`, mantendo dimensões
independentes e required verification quando contexto esperado não foi declarado.
Rodar testes de routing e regression suite; commit separado.

## T3 — matriz

Adicionar células conservadoras para formatos/operações/releases declarados no
prompt, sempre com fonte, data e limitation. Célula não fechada fica
`version_dependent` ou `unknown`; executar loader/offline bundle; commit.

## T4 — documentação e registros

Atualizar knowledge, skill, agentes e vNext. Regenerar mirrors/referência e
claims. Rodar gates de superfície, sincronização, locks e focused suite; commit.

## Validação final

Só após todos os commits: executar as nove batches da suíte completa, registrar
contagens no ship, criar build report/ship, push da branch e atualizar PR #118.
