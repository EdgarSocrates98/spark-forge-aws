---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender o núcleo determinístico existente com uma matriz version-aware, analyzer de routing/decisão e integração CLI/MCP, preservando facts e regras como fontes de evidência."
    tradeoffs:
      - "Reutiliza `sparkforge_aws/facts`, `rules/catalog`, knowledge e grafo existentes."
      - "Exige contratos novos para ownership, operação, modo de acesso e estados unresolved."
      - "Permite adicionar Glue, EMR e EMR Serverless sem duplicar diagnósticos."
  - id: B
    summary: "Adicionar somente documentação, skills e agentes especializados sem um motor executável novo."
    tradeoffs:
      - "Entrega navegação rápida e baixo risco de código."
      - "Não satisfaz routing, preflight, decisão version-aware ou testes negativos executáveis."
      - "Duplicaria conhecimento que já existe em facts e regras sem fechar o caminho de evidência."
  - id: C
    summary: "Criar uma camada autônoma de agentes e coletores live para administrar Lake Formation, RAM, IAM, S3 e KMS."
    tradeoffs:
      - "Poderia automatizar operações externas."
      - "Amplia superfície, autoridade e risco de segurança; conflita com o núcleo offline e least privilege do repositório."
      - "Não é necessário para diagnosticar fatos já coletados nem para provar compatibilidade de runtime."
chosen: A
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — exploração

## Perfil

`dev`: a mudança evolui o próprio SparkForge. A missão do operador autoriza a abordagem A e o ciclo completo, mas cada alteração externa de AWS continua fora do escopo de execução automática.

## Perguntas feitas, uma por vez

1. A mudança é no SparkForge ou em um job de operador? Resposta: no SparkForge; o prompt pede evolução arquitetural do repositório.
2. O sistema já possui fatos, regras e coletors de Lake Formation? Resposta: sim; `sparkforge_aws/facts/lakeformation.py`, `sparkforge_aws/facts/lakeformation_matrix.py`, `sparkforge_aws/lakeformation/graph.py`, `rules/catalog/lakeformation.yaml`, `rules/catalog/glue-cross-account.yaml` e testes correspondentes já existem.
3. O núcleo deve inferir permissão ou administrar AWS? Resposta: não; deve preservar evidence-first, estados `unresolved` e simulação IAM, sem conceder permissões nem alterar recursos.
4. Qual recorte fecha a primeira entrega? Resposta: capability/decision plane version-aware para Glue, EMR on EC2 e EMR Serverless; routing de contas/catálogos; decisão FGAC/FTA; credential-vending preflight; diagnóstico estruturado; integração de CLI/MCP; conhecimento, docs, skills e golden/negative fixtures.

## Abordagens

### A — Núcleo determinístico version-aware ⭐ Recomendada

Adicionar um contrato de arquitetura governada que consuma uma entrada declarativa e produza decisões com `observed`, `inferred`, `required_verification`, riscos e rollback. A matriz de capacidades separa engine, runtime, access model, format, operation, filesystem e cross-account. O analyzer não inventa owner: mantém `job_account_id`, `local_account_id`, `catalog_owner_account_id`, `producer_account_id`, `consumer_account_id` e `storage_account_id` como dimensões distintas.

O caminho será: facts/knowledge versionados → routing e capability lookup → decisão FGAC/FTA → credential-vending e cross-account checks → diagnóstico/preflight. A integração deve reutilizar os verbs e adapters existentes, declarando qualquer crescimento de superfície nos registros obrigatórios.

### B — Documentação/agents primeiro

Rejeitada para esta missão: o repositório já tem especialistas, skills e documentos parciais. Sem um núcleo executável, os negativos críticos — DynamicFrame FGAC em Glue 5.x, `glue.id` confundido com `glue.account-id`, `GetDataAccess` ausente e FGAC+FTA no EMR — continuam sem prova determinística.

### C — Automação live/autônoma

Rejeitada nesta evolução: coletors live existem, mas conceder/revogar LF, editar IAM/KMS, aceitar RAM ou registrar S3 é uma ação de postura de segurança. O SparkForge deve diagnosticar e propor com evidência; mutação exige autoridade e confirmação explícitas.

## Fontes verificadas

- AWS Glue — access control models: `https://docs.aws.amazon.com/glue/latest/dg/lake-formation-access-control-models.html` (consultado em 2026-09-30; separa FGAC/FTA e impacto operacional).
- AWS Glue — Full Table Access: `https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html` (consultado em 2026-09-30; Glue 5.0+, `GetDataAccess`, Hive/Iceberg, operações e incompatibilidade FGAC/FTA).
- AWS Glue — Lake Formation considerations: `https://docs.aws.amazon.com/glue/latest/dg/security-lf-enable-considerations.html` (consultado em 2026-09-30; Spark session, workers e resource links).
- Lake Formation — cross-account: `https://docs.aws.amazon.com/lake-formation/latest/dg/cross-data-sharing-lf.html` e `https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-prereqs.html` (consultado em 2026-09-30; RAM, resource links, IAMAllowedPrincipals e versões).
- Lake Formation Developer Guide: `https://docs.aws.amazon.com/lake-formation/latest/dg/lake-formation-dg.pdf` (consultado em 2026-09-30; cross-account v4/v5 e wildcard shares).
- EMR — FGAC: `https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-lf-enable.html` (consultado em 2026-09-30; EMR 6.15+).
- EMR — FTA: `https://docs.aws.amazon.com/emr/latest/ManagementGuide/lake-formation-unfiltered-ec2-access.html` (consultado em 2026-09-30; EMR 7.8+, filesystem e cross-account).
- EMR Serverless — Lake Formation: `https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/lake-formation-section.html` (consultado em 2026-09-30; disponibilidade por release).
- Lake Formation credential vending: `https://docs.aws.amazon.com/lake-formation/latest/dg/using-cred-vending.html` (consultado em 2026-09-30; APIs de credenciais temporárias).

## Escolha

A. A missão explicitamente solicita implementação arquitetural profunda, testes, docs, skills/agents e entrega por commits; o núcleo determinístico é a menor abordagem que satisfaz isso sem duplicar o que já existe ou conceder autoridade live.

## Decomposição aprovada

1. Contrato de entrada/saída e capability matrix para Glue, EMR EC2 e EMR Serverless.
2. `CatalogRoutingAnalyzer` com ownership/account dimensions e distinção `glue.id`/`glue.account-id`.
3. Decision engine FGAC/FTA por engine, versão, formato, operação e escopo cross-account.
4. Credential-vending/preflight checks e diagnósticos de camada metadata/data/credential/storage/encryption.
5. CLI/MCP, routing inteligente, knowledge packs, docs e skills/agent mirrors.
6. Golden path Iceberg cross-account Glue 5.1 e negativos obrigatórios, incluindo Glue 4→5.1 e EMR FGAC+FTA conflict.

## Limites preservados

- Nenhuma concessão/revogação de Lake Formation, IAM, KMS ou RAM.
- Nenhum valor de performance/custo inventado; custo/performance entram como impacto condicionado e medição futura.
- Nenhum `True` derivado de ausência de fact; estados `unresolved`, `unknown` e `not_applicable` permanecem distintos.
- Nenhuma duplicação de `facts`, regras ou matrices que já sejam fonte de verdade; extensões devem apontar para o arquivo existente ou substituí-lo com migração explícita.
