---
sdd: 1
feature: LAKE_FORMATION_OPERATIONAL_CLOSURE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_OPERATIONAL_CLOSURE/design.md
  sha256: "b8ff0d024da686a29c94395821c6cdd058196ae92de3e8d0b1ef097456ec9f39"
tasks:
  - id: T1
    files: [tests/test_lakeformation_operational_closure.py, sparkforge_aws/lakeformation/architecture.py]
    covers: [AC1, AC2]
    test: {path: tests/test_lakeformation_operational_closure.py, name: test_review_composes_code_iac_and_late_configuration}
  - id: T2
    files: [tests/test_lakeformation_operational_closure.py, knowledge/lakeformation/capability-matrix.yaml]
    covers: [AC3, AC6]
    test: {path: tests/test_lakeformation_operational_closure.py, name: test_review_builds_version_aware_migration_report}
  - id: T3
    files: [tests/test_lakeformation_operational_closure.py, sparkforge_aws/lakeformation/architecture.py]
    covers: [AC4, AC5]
    test: {path: tests/test_lakeformation_operational_closure.py, name: test_review_preflight_is_least_privilege_and_cross_reviewed}
  - id: T4
    files: [tests/test_lakeformation_operational_closure.py, sparkforge_aws/adapters/tools.py, skills/lakeformation-architecture/SKILL.md, agents/sf-lake-formation-specialist.md, agents/sf-terraform-specialist.md, knowledge/lakeformation/operational-closure.md, docs/guia/usos/lake-formation-operacional.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CAPABILITY-MATRIX.md, docs/vnext/KNOWLEDGE-MAP.md]
    covers: [AC7, AC8]
    test: {path: tests/test_lakeformation_operational_closure.py, name: test_cli_and_mcp_operational_review_parity}
---

# LAKE_FORMATION_OPERATIONAL_CLOSURE — plano

## T1 — revisão de código/IaC, configuração tardia e camadas de acesso

Escrever `tests/test_lakeformation_operational_closure.py` com payload declarativo
que contenha facts `pyspark.glue_context_init`, `pyspark.conf_set`,
`pyspark.read`, `tf.spark_conf`, `tf.attribute` e `spark.conf_effective`.
O teste deve falhar porque `review` ainda não existe. Implementar em
`sparkforge_aws/lakeformation/architecture.py` helpers puros que ancorem kind/source/line,
classifiquem DynamicFrame/direct S3, comparem a primeira operação com a linha da
configuração e mantenham fatos ausentes em `required_verification`.

Compor `access_explain`, `authorization` e `error_taxonomy` a partir do payload,
sem ler disco nem chamar AWS. Rodar o teste até verde. Gate vizinho: `ruff check`
nos dois arquivos. Commit: `feat(lakeformation): add evidence-first operational review`.

## T2 — migração e matriz de formato/operação

Adicionar teste para `migration: {from_runtime: 4.0, to_runtime: 5.1}` e para
Glue 6.0/EMR 7.12. O vermelho deve ser ausência de `migration` ou de células
version-aware. Atualizar `knowledge/lakeformation/capability-matrix.yaml` com
células explicitamente suportadas por fontes já bloqueadas e manter
`version_dependent`/`unknown` quando FTA/FGAC ou fonte oficial divergem.
Implementar relatório com mudanças breaking/semantic/security/performance/cost,
testing plan e rollback plan, sem porcentagens inventadas. Rodar os testes T2 e o
loader da matriz. Gate vizinho: `python scripts/verify_offline_bundle.py`.
Commit: `feat(lakeformation): close version-aware migration and format matrix`.

## T3 — preflight, least privilege, performance/FinOps e cross-review

Adicionar teste para ausência de GetDataAccess, RAM, resource link, registration,
IAMAllowedPrincipals e para benchmark/DPUSeconds ausentes. O vermelho deve ser
ausência de `preflight`, `root_cause`, `performance_finops` ou `cross_review`.
Implementar checks nomeados por layer, recomendações least-privilege sem
`Action: "*"`/`Resource: "*"`, hipóteses com evidência e verificação requerida,
impactos condicionais de FGAC/FTA e referências de especialistas cruzados.
Quando benchmark ou DPUSeconds não vierem, output deve dizer quais medidas
destravariam a conclusão. Gate vizinho: `ruff check` e focused suite completa.
Commit: `feat(lakeformation): add layered preflight and root-cause review`.

## T4 — integração, conhecimento, runbooks, agentes e VNX

Adicionar teste de paridade CLI/MCP e teste de âncoras nos documentos. Atualizar
descrição/schema da tool existente, skill e coordenadores; gerar espelhos e
referências com os scripts oficiais. Criar knowledge operacional e guia com os
runbooks Glue 5.1 Parquet/Iceberg, MERGE, credential vending, RAM, resource link,
FTA e EMR FGAC. Atualizar os três documentos VNX sem afirmar economia medida.
Rodar `sync_skills.py --check`, `gen_reference_docs.py`, `check_surface_lock.py`,
`check_vnext_claims.py`, `check_status_numbers.py --strict` e focused suite.
Commit: `docs(lakeformation): publish operational closure and runbooks`.
