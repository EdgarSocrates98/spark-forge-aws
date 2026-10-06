---
sdd: 1
feature: LAKE_FORMATION_OPERATIONAL_CLOSURE
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Compor o architecture decision engine com revisão operacional evidence-first fecha os critérios do prompt que ficaram além da matriz/routing, sem chamar AWS nem duplicar os extratores existentes."
  prediction: "Para entradas Glue/EMR declarativas com facts de PySpark/Terraform e erros de autorização, a saída terá revisão de código/IaC, configuração tardia, preflight, explain de acesso, autorização metadata/data, taxonomia/root-cause, migração, performance/FinOps sem números inventados e referências progressive-disclosure; entradas sem evidência permanecerão unresolved."
  experiment: "Adicionar testes vermelhos para cada contrato, implementar composição offline sobre analyze_architecture e facts já extraídos, atualizar knowledge/agentes/VNX e executar gates e suíte completa no ship."
acceptance:
  - id: AC1
    statement: "A revisão compõe PySpark, Spark config e Terraform sem reextrair nem inventar facts, detecta DynamicFrame/direct-S3 e configuração Lake Formation aplicada depois do primeiro acesso, e separa observado de required_verification."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_review_composes_code_iac_and_late_configuration"}
  - id: AC2
    statement: "A saída explica o caminho de acesso e separa autorização de metadata de autorização de dados/credenciais, classificando erros de catálogo, Lake Formation, credential vending, RAM, S3 e KMS."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_review_explains_access_and_root_cause_layers"}
  - id: AC3
    statement: "A revisão gera relatório de migração para Glue 4→5.1 e Glue 5.0→5.1 com breaking/semantic/security/performance/cost changes, plano de teste e rollback, preservando a capability version-aware."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_review_builds_version_aware_migration_report"}
  - id: AC4
    statement: "O preflight valida least privilege, IAMAllowedPrincipals/hybrid, RAM, resource link, GetDataAccess, registro e operações read/write; recomendações não usam Allow * nem bypass S3."
    guard: "A revisão T1 já compõe preflight e cross-review; estes testes permanecem guardas contra regressão enquanto T3 fecha a documentação e gates operacionais."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_review_preflight_is_least_privilege_and_cross_reviewed"}
  - id: AC5
    statement: "A análise de performance/FinOps expõe impacto condicional de FGAC/FTA e workers/latência/custo como medidas requeridas, usando números somente quando benchmark ou DPUSeconds declarados; contexto carregado é limitado por engine/runtime/model/format/operation."
    guard: "A revisão T1 já compõe performance_finops e progressive disclosure; estes testes permanecem guardas contra regressão enquanto T3 fecha a documentação e gates operacionais."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_review_preserves_evidence_and_progressive_disclosure"}
  - id: AC6
    statement: "A matriz operacional cobre operações e formatos Hive/Parquet/Iceberg/Hudi/Delta para Glue 5.1/6.0 e EMR 7.12, mantendo unknown quando as fontes oficiais divergem ou não fecham a célula."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_matrix_closure_keeps_format_and_source_boundaries"}
  - id: AC7
    statement: "CLI e MCP continuam retornando payload idêntico para a revisão operacional, sem ampliar a superfície com uma tool paralela."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_cli_and_mcp_operational_review_parity"}
  - id: AC8
    statement: "Knowledge, runbooks, skill, coordenadores e VNX documentam explain-access, root-cause, migração, cross-review e progressive disclosure com fontes oficiais e sem claim de ganho não medido."
    verified_by: {kind: test, ref: "tests/test_lakeformation_operational_closure.py::test_operational_closure_docs_and_vnx_are_anchored"}
success:
  - id: SC1
    metric: "Testes acceptance AC1–AC8 verdes após vermelho próprio"
    source: "python -m pytest tests/test_lakeformation_operational_closure.py -q"
  - id: SC2
    metric: "Payload CLI/MCP idêntico no mesmo input"
    source: "tests/test_lakeformation_operational_closure.py::test_cli_and_mcp_operational_review_parity"
  - id: SC3
    metric: "Divergências nos gates de knowledge, surface, claims, skills e SDD"
    source: "scripts/verify_offline_bundle.py, scripts/check_surface_lock.py, scripts/check_vnext_claims.py, sparkforge-aws sdd check"
out_of_scope:
  - "Conceder, revogar, simular ao vivo ou aceitar permissões Lake Formation, IAM, KMS ou RAM."
  - "Prometer ou estimar numericamente custo, latência, workers, tokens ou ganho sem benchmark/DPUSeconds observado."
  - "Substituir os extratores existentes de Terraform, PySpark, runtime, IAM, RAM, CloudTrail ou Lake Formation."
  - "Aplicar automaticamente mudanças no job, Terraform, S3, KMS ou Spark config."
unknowns:
  - id: U1
    blocks: []
    unlock: "Fonte oficial específica para cada combinação futura de engine, release, formato e operação; célula deve continuar unknown até a fonte ser registrada."
change_kinds: [knowledge_doc, agent_or_skill, tool_or_verb, claims]
---

# LAKE_FORMATION_OPERATIONAL_CLOSURE — requisitos

## Escopo

O PR anterior (`LAKE_FORMATION_FGAC_FTA_EVOLUTION`) fechou capability matrix,
routing e decision engine. Este delta fecha os critérios literais restantes do
prompt `prompt_evo_fgac_fta_espec.md`: revisão de código/IaC, configuração tardia,
explain de acesso, diagnóstico em camadas, migration report, preflight, runbooks,
least privilege, cross-review, progressive disclosure e a matriz de formatos.

O contrato permanece offline e declarativo. Facts continuam vindo dos verbos
determinísticos existentes; ausência de fact nunca vira `False`, `Allow *` ou
suporte implícito.

## Fontes version-aware

- AWS Glue — FGAC e configuração antes da primeira célula:
  `https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable.html`.
- AWS Glue — FTA e incompatibilidade FGAC/FTA:
  `https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html`.
- AWS Glue 5.1 e 6.0 — mudanças de runtime e OTF:
  `https://docs.aws.amazon.com/glue/latest/dg/migrating-version-51.html` e
  `https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html`.
- Lake Formation — cross-account/hybrid:
  `https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html`.

## Fechamento em relação ao prompt

AC1–AC4 do delta fecham os critérios de revisar Terraform/Spark/PySpark,
detectar configuração tardia, explicar acesso, distinguir metadata/data,
credential vending, RAM, KMS e root cause. AC5 fecha performance/FinOps sem
inventar medidas e economia de tokens. AC6 fecha a matriz de formato/operação e
as limitações de Glue 6.x. AC7–AC8 fecham integração, documentação, runbooks,
cross-review e VNX.
