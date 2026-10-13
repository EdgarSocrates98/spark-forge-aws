---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/explore.md
  sha256: "13341235402bde3a7a744d7f066d4fd088c51f8033ea52cc7faba0a951fb1b41"
hypothesis:
  claim: "Um contrato arquitetural determinístico que separa engine/runtime, modelo FGAC/FTA, formato, operação, ownership de catálogo, credential vending e cross-account reduzirá recomendações genéricas e permitirá diagnosticar os caminhos críticos do prompt sem administrar AWS."
  prediction: "Os cenários Glue 4→5.1, Glue 5.1 FGAC/FTA, EMR FGAC/FTA, Iceberg cross-account e falhas de credential vending produzirão decisões version-aware, negativas nomeadas ou unresolved quando faltar evidência; CLI e MCP devolverão o mesmo payload."
  experiment: "Executar testes unitários e golden/negative scenarios do analyzer, carregar a matriz oficial, comparar CLI/MCP e rodar os gates de knowledge, surface, skills, claims e a suíte completa ao final da feature."
acceptance:
  - id: AC1
    statement: "O contrato preserva separadamente job, local, catálogo produtor/consumidor, storage e owner account, sem inferir igualdade entre IDs."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_routing_preserves_account_ownership_dimensions"}
  - id: AC2
    statement: "`glue.id` e `glue.account-id` são propriedades distintas e divergência ou ausência produz unresolved com verificação requerida."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_routing_does_not_alias_glue_id_and_account_id"}
  - id: AC3
    statement: "Glue 4.0 com DynamicFrame/GlueContext em caminho Lake Formation gera alerta de migração arquitetural para Glue 5.x Spark-native, sem sugerir acesso direto ao S3 como correção."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_glue4_dynamicframe_to_glue5_fgac_is_migration"}
  - id: AC4
    statement: "Glue 5.0/5.1 diferencia FGAC de FTA por formato e operação e recusa configuração simultânea no mesmo job."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_glue_access_model_is_version_and_operation_aware"}
  - id: AC5
    statement: "EMR EC2 e EMR Serverless usam availability por release, incluindo EMR FGAC, FTA, filesystem e conflito FGAC+FTA; release não coberta fica unresolved."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_emr_release_capabilities_are_version_aware"}
  - id: AC6
    statement: "Leitura e escrita são avaliadas como operações distintas, com permissões metadata, Lake Formation, IAM e storage não colapsadas em SELECT."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_read_and_write_authorization_are_separate"}
  - id: AC7
    statement: "FTA/caminhos governados verificam `lakeformation:GetDataAccess`, aplicação de credential vending, filesystem compatível e retornam o layer da falha sem recomendar S3 Allow genérico."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_credential_vending_preflight_is_layered"}
  - id: AC8
    statement: "Cross-account valida RAM/version/resource link/IAMAllowedPrincipals/hybrid como dimensões independentes e nomeia evidência ausente como unresolved."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_cross_account_governance_requires_independent_evidence"}
  - id: AC9
    statement: "O golden path Glue 5.1, Account B lendo Iceberg governado em A e escrevendo Iceberg governado em B, retorna arquitetura consistente sem hardcode de contas."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_golden_path_glue51_cross_account_iceberg"}
  - id: AC10
    statement: "Os negativos obrigatórios não recomendam DynamicFrame FGAC no Glue 5.x, alias de account IDs, direct parquet para tabela governada, S3-only fix ou FGAC+FTA no EMR."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed"}
  - id: AC11
    statement: "O verbo CLI e a tool MCP expõem o mesmo resultado version-aware para o contrato de arquitetura."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity"}
  - id: AC12
    statement: "Conhecimento, skill/coordenador e VNX documentam o contrato, as fontes oficiais, limitações e o caminho progressive-disclosure sem claims de custo/performance não medidos."
    verified_by: {kind: test, ref: "tests/test_lakeformation_architecture.py::test_architecture_docs_and_vnext_are_anchored"}
success:
  - id: SC1
    metric: "Cenários acceptance AC1–AC10 que produzem decisão correta, refusal ou unresolved nomeado"
    source: "python -m pytest tests/test_lakeformation_architecture.py -q"
  - id: SC2
    metric: "Diferenças de payload entre CLI e MCP no mesmo input"
    source: "tests/test_lakeformation_architecture.py::test_cli_and_mcp_architecture_parity"
  - id: SC3
    metric: "Células da matriz com source, version scope e estado fechado"
    source: "tests/test_lakeformation_architecture.py::test_capability_matrix_is_source_backed"
out_of_scope:
  - "Conceder ou revogar permissões Lake Formation, IAM, KMS ou RAM."
  - "Chamar AWS em runtime do analyzer ou inferir uma política ausente."
  - "Prometer ganho de custo, latência, workers ou tokens sem benchmark medido."
  - "Cobrir Glue 6.x Lake Formation antes de ler e registrar fonte oficial específica para esse eixo."
  - "Implementar mutações Terraform ou um novo sistema de agentes autônomos."
unknowns:
  - id: U1
    blocks: []
    unlock: "Documentação oficial específica para cada célula ainda desconhecida da matriz deve ser adicionada antes de mudar seu estado de unresolved."
case_id: null
change_kinds: [knowledge_doc, tool_or_verb, agent_or_skill, claims]
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — requisitos

## Problema

O SparkForge já possui facts, regras e procedimentos Lake Formation, mas a missão combinada exige uma resposta arquitetural que atravesse runtime, modelo de acesso, catálogo, contas, operação e credential path. Hoje esses eixos estão dispersos: a matriz é Glue-specific, o doctor aceita dumps simplificados sem versão, e não há um contrato único que impeça confundir catálogo produtor com conta do job ou SELECT com autorização de escrita.

## Critérios

Os 12 acceptance criteria no frontmatter são obrigatórios. Cada um é verificável por teste nomeado e deverá ter vermelho observado antes da implementação e verde depois. O ship só fecha após os testes focados, gates de registros e suíte completa passarem.

## Conhecimento version-aware

O design deve citar as páginas oficiais já verificadas no `explore.md` e manter `service`, `engine`, `runtime`, `access_model`, `format`, `operation`, `source`, `last_verified` e `limitations` nas células de conhecimento. A matriz atual de Glue continua fonte detalhada para seus eixos; o novo contrato deve compor sem duplicar ou sobrescrever suas células.

## Segurança e evidência

Toda decisão crítica terá `observed`, `inferred`, `required_verification`, `risks`, `rollback` e estado `supported|limited|read_only|version_dependent|not_supported|unknown`. Ausência de RAM, KMS, grant, registration ou IAM simulation nunca vira `False` silencioso nem `Allow *` como recomendação.
