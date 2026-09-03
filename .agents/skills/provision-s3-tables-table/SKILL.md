---
name: provision-s3-tables-table
description: Use quando for criar uma tabela Iceberg gerenciada por Amazon S3 Tables (o produto `s3tables`, não o Glue Data Catalog tradicional) — table bucket, namespace, tabela, schema, particionamento, integração com o catálogo `s3tablescatalog` e IAM no namespace `s3tables:*`. Use também quando a pergunta for "como crio uma tabela Iceberg sem gerenciar compaction", "S3 Tables vale vs Glue Data Catalog" ou "por que `s3:*` não funciona no S3 Tables", mesmo sem citar o produto pelo nome. NÃO use para criar tabela no Glue Data Catalog tradicional (esse caminho não está aqui — use `design-s3-data-lake` para o design e `optimize-iceberg-table` para a manutenção), nem para ingerir dado (procedimento de carga é outro), nem para consultar tabela existente (`optimize-athena-queries`). Se você está prestes a rodar `aws s3tables create-table-bucket` sem checar tabelas existentes, pare — o passo 1 exige o inventário, e criar sobre nome existente é silencioso.
---

# Provisionar tabela no Amazon S3 Tables

Amazon S3 Tables é um produto distinto do Glue Data Catalog: oferece tabelas
Iceberg **gerenciadas** com compaction e snapshot management automáticos,
consultáveis por Athena e engines compatíveis com Iceberg. O catálogo é
`s3tablescatalog`, não o Glue padrão, e o namespace de IAM é `s3tables:*`, não
`s3:*` — confundir os dois é o erro mais comum aqui.

Esta skill é **procedimento operacional que muta infraestrutura AWS ao vivo**.
Ela não é um gatilho do motor SparkForge: o motor é offline e determinístico,
lê artefato em disco. Aqui você executa comandos `aws s3tables` / `aws glue`
reais. Por isso a fronteira `## Não faz` é estrita e o despacho é recusado.

## Procedimento

### 0. Verifique dependências

- Confirme região alvo e credenciais: `aws sts get-caller-identity`.
- Verifique se `aws s3tables` e `aws glue` estão disponíveis no ambiente.
- Se houver tabela existente no Glue Data Catalog com o mesmo nome e ela for
  **não-S3-Tables**, pare: delegue a resolução para o operador confirmar antes
  de criar — sobrescrever é silencioso.

### 1. Inventarie o que existe

```bash
aws glue get-tables --database-name <NOME>
aws s3tables list-table-buckets --region <REGIAO>
```

| O que achar | Ação |
|---|---|
| Nome de banco "fuzzy" ("nosso db de analytics") | Pare — peça ao operador para resolver o nome exato |
| Tabela não-S3-Tables com nome coincidente | Pare — não crie até o operador confirmar |
| Tabela S3 Tables existente com nome coincidente | Verifique compatibilidade de schema; reutilize se compatível, recrie só com confirmação |
| Nada coincidente | Prossiga (passos 2–7) |
| Operador pediu explicitamente tabela nova | Pule as checagens, prossiga |

### 2. Defina o schema

- Peça nome da tabela, colunas, tipos e estratégia de partição **antes** de criar.
- Nomes em **minúsculo** — Glue rejeita mixed case com `GENERIC_INTERNAL_ERROR`.
- Namespace e nome de tabela **sem hifens**.
- Sugira colunas de partição a partir dos padrões de acesso declarados.
- Para tipos Iceberg, particionamento e naming, consulte a doc oficial AWS
  (referência em `## Proveniência`) — não reproduza de memória.

### 3. Crie o table bucket

```bash
aws s3tables create-table-bucket --name <BUCKET> --region <REGIAO>
```

Capture o `table-bucket-arn`. Nome: 3–63 chars, minúsculo, números, hifens.
Encriptação (SSE-S3 default, SSE-KMS) e storage class são definidas na criação.
Se SSE-KMS, a policy da chave KMS **deve** permitir o service principal de
manutenção do S3 Tables ler o dado — consulte a doc AWS para a policy exata.

### 4. Crie o namespace

```bash
aws s3tables create-namespace --table-bucket-arn <ARN> --namespace <NS>
```

Liste namespaces existentes primeiro; sugira reuso se relevante. Minúsculo,
sem hifens.

### 5. Crie a integração com o Glue Data Catalog

O catálogo `s3tablescatalog` é **um por região por conta**. Verifique se existe:

```bash
aws glue get-catalog --catalog-id s3tablescatalog
```

Se não existir, crie (exige `glue:CreateCatalog`, `glue:passConnection`):

```bash
aws glue create-catalog --name "s3tablescatalog" --catalog-input '{ ... }'
```

O JSON do `--catalog-input` tem a forma exata na doc AWS (referência em
`## Proveniência`) — não reproduza de memória, o campo
`FederatedCatalog.Identifier` precisa do ARN do bucket com wildcard.

### 6. Configure IAM

S3 Tables usa `s3tables:*`, **não** `s3:*`. Permissões do principal que consulta:

- Bucket policy: `s3tables:GetTableBucket`, `GetNamespace`, `GetTable`,
  `GetTableMetadataLocation`, `GetTableData`
- IAM policy: `glue:GetCatalog`, `GetDatabase`, `GetTable`

Scope para os ARN patterns corretos. **Não** conceda mais que o necessário.
**Não** crie IAM roles automaticamente — verifique os existentes e guie o
operador. Peça o ARN do principal que vai consultar.

### 7. Crie a tabela

Caminho default — S3 Tables API:

```bash
aws s3tables create-table \
  --table-bucket-arn <ARN> \
  --namespace <NS> \
  --name <TABELA> \
  --format ICEBERG \
  --metadata '<METADATA_JSON>'
```

O `metadata` JSON aninha sob `"iceberg"`: `schema.fields` (name, type, required)
e `partitionSpec.fields` (sourceId, fieldId, transform, name). `sourceId` **deve**
referenciar um field ID válido do schema. Para tipos complexos (list, map,
struct) use `schemaV2` com field IDs explícitos.

Caminhos alternativos (consulte a doc AWS):
- **Athena DDL**: só se o operador pedir SQL explicitamente. Não ponha
  `LOCATION` — S3 Tables gerencia o storage; `LOCATION` rejeita com
  "Table location can not be specified".
- **Spark DDL via Glue ETL**: passe por `--conf` em job args, **não** por
  `spark.conf.set()` em runtime.

### 8. Verifique

```bash
aws s3tables get-table --table-bucket-arn <ARN> --namespace <NS> --name <TABELA>
```

E confirme queryability via Athena com `DESCRIBE`, passando o catalog em
`--query-execution-context` (não no SQL):

```bash
aws athena start-query-execution --query-string "DESCRIBE <tabela>" \
  --query-execution-context '{"Catalog":"s3tablescatalog/<BUCKET>","Database":"<NS>"}'
```

Apresente resumo: bucket ARN, namespace, tabela, schema, partições.

## Referência rápida

| Passo | Comando | O que faz |
|---|---|---|
| 1 | `aws s3tables list-table-buckets` | Inventário antes de criar |
| 3 | `aws s3tables create-table-bucket` | Cria o table bucket |
| 4 | `aws s3tables create-namespace` | Cria namespace no bucket |
| 5 | `aws glue get-catalog` / `create-catalog` | Integração `s3tablescatalog` |
| 7 | `aws s3tables create-table` | Cria a tabela Iceberg |
| 8 | `aws s3tables get-table` | Verificação |

Namespace de IAM: `s3tables:*`, **não** `s3:*`. Catálogo: `s3tablescatalog`, um por região por conta.

## Quando NÃO usar

- **Glue Data Catalog tradicional**: este procedimento é específico de S3
  Tables. Para Iceberg no Glue Data Catalog, o design é `design-s3-data-lake` e
  a manutenção é `optimize-iceberg-table`.
- **Ingestão de dado**: criar a tabela vazia é o passo 1–7; carregar dado é
  outro procedimento (a doc AWS chama a skill `ingesting-into-data-lake`).
- **Query em tabela existente**: `optimize-athena-queries` cobre leitura.
- **Avaliar upgrade de format-version Iceberg**: `iceberg-v3-readiness`.
- **Diagnosticar small files / snapshots acumulados**: `optimize-iceberg-table`
  sobre os metadata tables.

## Red flags

- Rodar `create-table-bucket` sem `list-table-buckets` antes — criar sobre nome
  existente é silencioso.
- Usar `s3:*` em IAM quando o produto é `s3tables:*` — `AccessDeniedException`
  com policy de `s3` é o sintoma, e a correção é trocar o namespace, não
  ampliar a policy.
- Misturar mixed case ou hífen em namespace/nome de tabela — Glue rejeita com
  `GENERIC_INTERNAL_ERROR`, e a mensagem não diz que foi o nome.
- Reproduzir o JSON do `create-catalog` ou o `metadata` do `create-table` de
  memória — a forma exata está na doc AWS e muda com o produto. Consulte a
  referência em `## Proveniência`.
- Declarar `LOCATION` em Athena DDL — S3 Tables gerencia o storage e rejeita.
- Criar a integração `s3tablescatalog` mais de uma vez por região — é uma por
  conta por região.

## Não faz

Esta skill **não executa** criação de bucket, namespace, tabela ou catalog
integration sem confirmação explícita do operador para cada comando de
escrita. Ela **recomenda** o comando, exibe o que ele faz, e **sobe a decisão**
a quem pode ser perguntado — o operador na sessão, ou o agente pai que
despachou. Dentro de um subagente, obter essa confirmação é **impossível**
(`ask_user_question` é sempre negado a subagente), e por isso esta skill **não
despacha**.

Manutenção destrutiva — `drop-table`, `delete-table-bucket`, expiração de
snapshot — você **não executa**. Recomende, e a confirmação de escopo e
retenção sobe a quem tem a pergunta disponível.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill
`specialized-skills/storage-skills/creating-data-lake-table`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa do procedimento e dos `references/` (access-control, best-practices,
athena-ddl-path, table-creation-glue-etl) — esta é uma adaptação ao contrato
SparkForge (PT-BR, fronteira de manutenção, não-despachável), e **pode
desatualizar** quando a AWS atualizar o procedimento. S3 Tables é produto novo:
antes de reproduzir JSON de comando, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme o
runtime e a região; nenhum número sem `fact_id` (aqui, fact vem do artefato de
`describe`/`get`, não de inspeção); `validate_output` antes de apresentar;
manutenção destrutiva você **não executa** — recomende, e a confirmação de
escopo e retenção **sobe a quem pode ser perguntado**: o operador na sessão,
ou o agente pai que despachou.
