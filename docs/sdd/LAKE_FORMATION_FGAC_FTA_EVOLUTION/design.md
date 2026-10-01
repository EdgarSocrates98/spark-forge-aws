---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_EVOLUTION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_EVOLUTION/define.md
  sha256: "668ab254232f705655e49def53a701793726f0bc8c5eab78862100155e561e18"
files:
  - {path: tests/test_lakeformation_architecture.py, action: create, reason: "Testes red/green do contrato, routing, decision engine, preflight, golden/negative scenarios, CLI/MCP parity e docs."}
  - {path: sparkforge/lakeformation/capabilities.py, action: create, reason: "Loader validado da matriz arquitetural cross-engine; reusa knowledge_ref e estados fechados."}
  - {path: sparkforge/lakeformation/catalog_routing.py, action: create, reason: "Resolve ownership e roteamento de catálogo sem aliasar glue.id, glue.account-id ou account IDs."}
  - {path: sparkforge/lakeformation/architecture.py, action: create, reason: "Decision engine puro que compõe matriz, routing, modelo, operação, cross-account e credential vending."}
  - {path: knowledge/lakeformation/capability-matrix.yaml, action: create, reason: "Fonte version-aware para Glue, EMR EC2 e EMR Serverless com source, last_verified e limitations por célula."}
  - {path: knowledge/lakeformation/architecture.md, action: create, reason: "Contrato humano de observed/inferred/required verification e limites do analyzer."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Expor composição lakeformation_architect sem leitura de artefato nem chamada AWS."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Adicionar `sparkforge lakeformation architect --input` ao surface existente."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Registrar schema e handler MCP com o mesmo payload da CLI."}
  - {path: agents/sf-lake-formation-specialist.md, action: modify, reason: "Fazer o coordenador usar o skill de arquitetura e declarar o novo procedimento."}
  - {path: agents/sf-runtime-specialist.md, action: modify, reason: "Adicionar o skill ao eixo de compatibilidade Glue/EMR sem criar agente paralelo."}
  - {path: skills/lakeformation-architecture/SKILL.md, action: create, reason: "Procedimento progressive-disclosure para routing, decision e preflight; fonte para espelhos gerados."}
  - {path: sparkforge/integrate/render.py, action: modify, reason: "Registrar a decisão de despacho da nova skill no renderizador canônico."}
  - {path: tests/test_sync_render.py, action: modify, reason: "Fixar relação medida entre nova skill e coordenadores."}
  - {path: tests/test_adapters_mcp_compact.py, action: modify, reason: "Atualizar contadores de superfície full após declarar a nova tool."}
  - {path: tests/test_host_surface_contracts.py, action: modify, reason: "Atualizar contrato de tamanho da superfície MCP após declarar a nova tool."}
  - {path: tests/test_fixtures_golden_mcp_parity.py, action: modify, reason: "Declarar a nova tool no allowlist de migração do golden MCP."}
  - {path: fixtures/knowledge_drift/lf_consideracoes/expected/result.json, action: modify, reason: "Regenerar impacto do documento knowledge novo pelo mecanismo oficial de drift."}
  - {path: manifest.json, action: modify, reason: "Publicar skill e tool novas no manifesto instalado."}
  - {path: docs/surface.lock.json, action: modify, reason: "Declarar crescimento mensurado da superfície MCP e skills."}
  - {path: docs/guia/usos/lake-formation-e-acesso.md, action: modify, reason: "Documentar o contrato novo, CLI e exemplos version-aware."}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "Registrar a camada architecture/decision plane como evolução do vNext."}
  - {path: docs/vnext/CAPABILITY-MATRIX.md, action: modify, reason: "Registrar matriz cross-engine e estados unknown/unresolved sem claim de suporte ausente."}
  - {path: docs/vnext/KNOWLEDGE-MAP.md, action: modify, reason: "Mapear knowledge matrix e progressive-disclosure para os especialistas existentes."}
  - {path: docs/claims.lock.json, action: modify, reason: "Atualizar claims do vNext após documentar a nova capacidade."}
decisions:
  - id: D1
    choice: "Compor a matriz arquitetural com a matriz Glue existente, mantendo fontes detalhadas por domínio e sem duplicar facts/rules."
    rejected: ["Substituir `knowledge/glue/lakeformation-matrix.yaml` por uma matriz única cross-engine, que quebraria consumidores e perderia o eixo detalhado Glue."]
    rollback: "git revert do commit da matriz e do loader; o diagnostico volta a usar somente `sparkforge/facts/lakeformation_matrix.py`."
  - id: D2
    choice: "Representar decisões como observed/inferred/required_verification com estados `supported`, `limited`, `read_only`, `version_dependent`, `not_supported` e `unknown`."
    rejected: ["Retornar apenas boolean supported, que confundiria ausência de fonte com incompatibilidade.", "Emitir Finding para toda decisão, que misturaria composição arquitetural com julgamento de regra."]
    rollback: "git revert do módulo `sparkforge/lakeformation/architecture.py`; facts/rules anteriores continuam intactos."
  - id: D3
    choice: "Usar input JSON declarativo para CLI/MCP, validado antes da decisão, sem coletar AWS nem ler arquivos arbitrários."
    rejected: ["Inferir contas a partir do ARN do job ou credencial corrente.", "Adicionar chamadas boto3 ao analyzer offline."]
    rollback: "git revert do adapter/CLI/MCP e remover o skill; nenhuma infraestrutura externa é alterada."
  - id: D4
    choice: "Modelar Glue, EMR EC2 e EMR Serverless por engine/release, formato e operação, com células unresolved quando a documentação não fecha."
    rejected: ["Aplicar regras Glue ao EMR por analogia.", "Preencher Glue 6.x por extrapolação do 5.1."]
    rollback: "Remover as células da matriz cuja fonte for invalidada e manter o estado `unknown`; o loader recusa fonte ausente."
  - id: D5
    choice: "Atualizar o coordenador e um skill especializado, sincronizando os espelhos, em vez de criar uma família de agentes novos."
    rejected: ["Criar oito agentes independentes antes de existir artefato que os diferencie.", "Colocar todo o conteúdo no agente e duplicar knowledge."]
    rollback: "git revert do skill/agent source e executar `python scripts/sync_skills.py` para restaurar os espelhos."
covers:
  - {part: "capability matrix and loader", acceptance: [AC3, AC4, AC5, AC12]}
  - {part: "catalog routing", acceptance: [AC1, AC2, AC8, AC9]}
  - {part: "architecture decision and preflight", acceptance: [AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC10]}
  - {part: "CLI/MCP adapter", acceptance: [AC11]}
  - {part: "knowledge, skill, docs and vNext", acceptance: [AC12]}
---

# LAKE_FORMATION_FGAC_FTA_EVOLUTION — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| capability matrix | `knowledge/lakeformation/capability-matrix.yaml`, `sparkforge/lakeformation/capabilities.py`, tests | AC3, AC4, AC5, AC12 |
| catalog routing | `sparkforge/lakeformation/catalog_routing.py`, tests | AC1, AC2, AC8, AC9 |
| architecture decision | `sparkforge/lakeformation/architecture.py`, tests | AC3–AC10 |
| surface integration | `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, tests | AC11 |
| knowledge and human contract | `knowledge/lakeformation/architecture.md`, skill, agents, docs and VNX | AC12 |

## Contrato de entrada

```yaml
engine: glue | emr_ec2 | emr_serverless
runtime: "5.1"
job_account_id: "..."
local_account_id: "..."
source_account_id: "..."
target_account_id: "..."
source_catalog: {name: producer_catalog, owner_account_id: "...", glue_id: "...", glue_account_id: "..."}
target_catalog: {name: local_catalog, owner_account_id: "...", glue_id: "...", glue_account_id: "..."}
source_format: iceberg
target_format: iceberg
access_model: fgac | fta | unknown
operation: read | insert | update | delete | merge | ddl
api: spark_sql | dataframe | dynamicframe | spark_catalog | direct_s3
cross_account: true
evidence:
  ram: accepted | pending | absent | unknown
  resource_link: present | absent | unknown
  iam_get_data_access: allowed | denied | unknown
  lakeformation_permission: select | all | super | absent | unknown
  registered_location: true | false | unknown
  application_integration: enabled | disabled | unknown
  filesystem: emrfs | s3a | unknown
```

Os account IDs são campos independentes; `glue.id` e `glue.account-id` não são normalizados para uma chave única. A ausência de evidência não escolhe uma conta nem retorna `supported`.

## Contrato de saída

```yaml
status: consistent | blocked | unresolved
decision:
  access_model: FGAC | FTA | migration_required | unresolved
  capability: supported | limited | read_only | version_dependent | not_supported | unknown
  observed: []
  inferred: []
  required_verification: []
  risks: []
  rollback: []
checks: []
routing: {}
```

O engine não concede, revoga, testa AWS ou propõe `Action: "*"`. Para `blocked`, o output nomeia a camada e a evidência; para `unresolved`, nomeia o campo que destrava a conclusão.

## Conhecimento consultado

- `sparkforge rules lookup --category lakeformation-fgac` e `--category cross-account`: regras existentes `SF-LF`/`SF-XACC`, inclusive estados unresolved e runtime scope.
- `sparkforge knowledge path --file knowledge/glue/lakeformation-fgac.md`: contrato Glue FGAC/FTA e limites já versionados no repositório.
- `sparkforge knowledge path --file knowledge/glue/lakeformation-matrix.yaml`: matriz Glue detalhada existente, composta e não substituída.
- AWS Glue FTA: `https://docs.aws.amazon.com/glue/latest/dg/security-access-control-fta.html`, verificado em 2026-09-30.
- AWS EMR FGAC/FTA: `https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-lf-enable.html` e `https://docs.aws.amazon.com/emr/latest/ManagementGuide/lake-formation-unfiltered-ec2-access.html`, verificados em 2026-09-30.
- AWS EMR Serverless Lake Formation: `https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/lake-formation-section.html`, verificado em 2026-09-30.
- AWS Lake Formation cross-account/RAM: `https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-prereqs.html`, verificado em 2026-09-30.

## Rollback geral

Reverter os commits de tarefa em ordem inversa. O código novo é offline e não tem migração de estado; retirar o CLI/MCP remove a superfície sem modificar dados ou permissões. Se uma fonte oficial for invalidada, a célula volta a `unknown`/`unresolved` em novo commit, nunca para um default otimista.
