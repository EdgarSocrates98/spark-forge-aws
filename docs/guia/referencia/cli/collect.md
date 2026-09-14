<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge collect`

Coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge collect athena-workgroup`](#sparkforge-collect-athena-workgroup) | Baixa a configuracao de um workgroup via a API do Athena. |
| [`sparkforge collect cloudwatch`](#sparkforge-collect-cloudwatch) | Baixa metricas de observabilidade Glue via CloudWatch. |
| [`sparkforge collect cloudwatch-logs`](#sparkforge-collect-cloudwatch-logs) | Baixa o LOG do run no CloudWatch Logs (o caminho das assinaturas de mensagem). |
| [`sparkforge collect emr-cluster`](#sparkforge-collect-emr-cluster) | Baixa describe-cluster, grupos/fleets, bootstrap actions e as politicas de scaling de um cluster EMR on EC2. |
| [`sparkforge collect emr-eks`](#sparkforge-collect-emr-eks) | Baixa describe-virtual-cluster e describe-job-run de uma execucao Amazon EMR on EKS e grava as duas respostas num arquivo so. Duas chamadas, nao uma: no `emr-containers` cluster virtual e execucao sao APIs separadas. |
| [`sparkforge collect emr-serverless`](#sparkforge-collect-emr-serverless) | Baixa get-application de uma application EMR Serverless. Uma chamada, nao seis: capacidade, auto-stop, runtimeConfiguration e monitoramento chegam no mesmo objeto. |
| [`sparkforge collect event-log`](#sparkforge-collect-event-log) | Baixa o Spark event log de um job run via S3. |
| [`sparkforge collect glue-job`](#sparkforge-collect-glue-job) | Baixa a definicao de um job via a API do Glue. |
| [`sparkforge collect glue-job-runs`](#sparkforge-collect-glue-job-runs) | Baixa o historico de execucoes de um job, um artefato por run terminal. |
| [`sparkforge collect glue-resource-link`](#sparkforge-collect-glue-resource-link) | Le o resource link na conta consumidora e o recurso de origem que ele declara. |
| [`sparkforge collect iam-access`](#sparkforge-collect-iam-access) | Simula acoes contra um role via SimulatePrincipalPolicy e grava a decisao. |
| [`sparkforge collect iceberg-metadata`](#sparkforge-collect-iceberg-metadata) | Consulta metadata tables Iceberg de uma tabela via Athena. |
| [`sparkforge collect lakeformation`](#sparkforge-collect-lakeformation) | Coleta grant, registro de localizacao S3 e data lake settings de UMA tabela. |
| [`sparkforge collect parquet-footer`](#sparkforge-collect-parquet-footer) | Le so o FOOTER dos Parquet de um prefixo (diretorio local ou s3://): row group, estatistica por coluna e sort order. Nenhuma linha de dado. Exige pyarrow. |
| [`sparkforge collect verify`](#sparkforge-collect-verify) | Verifica presenca e integridade de todos os artefatos do manifesto. |

## `sparkforge collect athena-workgroup`

Baixa a configuracao de um workgroup via a API do Athena.

```bash
sparkforge collect athena-workgroup --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--workgroup` | sim | texto |  |  |  |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect cloudwatch`

Baixa metricas de observabilidade Glue via CloudWatch.

```bash
sparkforge collect cloudwatch --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--job-name` | sim | texto |  |  |  |
| `--job-run` | sim | texto |  |  |  |
| `--start` | sim | texto |  |  | Inicio ISO 8601. |
| `--end` | sim | texto |  |  | Fim ISO 8601. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect cloudwatch-logs`

Baixa o LOG do run no CloudWatch Logs (o caminho das assinaturas de mensagem).

```bash
sparkforge collect cloudwatch-logs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--job-name` | sim | texto |  |  |  |
| `--job-run` | sim | texto |  |  |  |
| `--log-group` | sim | texto |  |  | Log group. Sem default -- `/aws-glue/jobs/error`, `/aws-glue/jobs/output` e `/aws-glue/jobs/logs-v2` tem conteudo diferente. |
| `--start` | sim | texto |  |  | Inicio ISO 8601. |
| `--end` | sim | texto |  |  | Fim ISO 8601. |
| `--filter-pattern` | não | texto |  | `` | Filtro do CloudWatch Logs, aplicado no servidor. Declara a relevancia. |
| `--max-events` | não | texto |  | `500` | Teto de eventos. Quando morde, o artefato sai com truncated: true. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect emr-cluster`

Baixa describe-cluster, grupos/fleets, bootstrap actions e as politicas de scaling de um cluster EMR on EC2.

```bash
sparkforge collect emr-cluster --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--cluster-id` | sim | texto |  |  | j-XXXXXXXXXXXXX |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect emr-eks`

Baixa describe-virtual-cluster e describe-job-run de uma execucao Amazon EMR on EKS e grava as duas respostas num arquivo so. Duas chamadas, nao uma: no `emr-containers` cluster virtual e execucao sao APIs separadas.

```bash
sparkforge collect emr-eks --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--virtual-cluster-id` | sim | texto |  |  | Id do cluster virtual. Nome NAO serve: `DescribeJobRun` exige o id. |
| `--job-run-id` | sim | texto |  |  | Id da execucao. Os DOIS ids sao obrigatorios porque `DescribeJobRun` exige `virtualClusterId` junto do `id`. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect emr-serverless`

Baixa get-application de uma application EMR Serverless. Uma chamada, nao seis: capacidade, auto-stop, runtimeConfiguration e monitoramento chegam no mesmo objeto.

```bash
sparkforge collect emr-serverless --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--application-id` | sim | texto |  |  | Id da application (`00fXXXXXXXXXXXXX`). Nome NAO serve: e opcional na API e nao ha fonte que o declare unico. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect event-log`

Baixa o Spark event log de um job run via S3.

```bash
sparkforge collect event-log --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--job-run` | sim | texto |  |  |  |
| `--bucket` | sim | texto |  |  |  |
| `--prefix` | sim | texto |  |  |  |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect glue-job`

Baixa a definicao de um job via a API do Glue.

```bash
sparkforge collect glue-job --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--job-name` | sim | texto |  |  |  |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect glue-job-runs`

Baixa o historico de execucoes de um job, um artefato por run terminal.

```bash
sparkforge collect glue-job-runs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--job-name` | sim | texto |  |  |  |
| `--max-runs` | não | texto |  | `30` | Teto de paginacao. A API devolve do mais recente para tras. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect glue-resource-link`

Le o resource link na conta consumidora e o recurso de origem que ele declara.

```bash
sparkforge collect glue-resource-link --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--database` | sim | texto |  |  | Banco do link na conta consumidora. |
| `--table` | não | texto |  | `` | Nome do link de TABELA. Sem ele o alvo e um BANCO -- e a comparacao de nome muda, porque `TargetDatabase` nao tem campo `Name`. |
| `--catalog-id` | não | texto |  | `` | Id da conta CONSUMIDORA, onde o link mora. O catalogo de origem sai medido do proprio link e nunca e passado a mao. |
| `--no-verify-target` | não | liga/desliga |  |  | Pula a leitura do recurso de ORIGEM. O default e conferir: link que aponta para lugar nenhum e o defeito que este coletor existe para achar. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect iam-access`

Simula acoes contra um role via SimulatePrincipalPolicy e grava a decisao.

```bash
sparkforge collect iam-access --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--role-arn` | sim | texto |  |  | ARN do role a simular -- tipicamente o runtime role do job. |
| `--action` | não | texto | sim |  | Acao a simular. Repetivel. Sem ela, a lista default de Lake Formation e Glue -- e passar a lista inteira quando a pergunta e sobre UMA escrita produz decisoes que nao dizem nada sobre o caso. |
| `--resource-arn` | não | texto | sim |  | Recurso contra o qual simular. Repetivel. Sem ele a resposta e sobre `*`. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect iceberg-metadata`

Consulta metadata tables Iceberg de uma tabela via Athena.

```bash
sparkforge collect iceberg-metadata --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--table` | sim | texto |  |  | db.tabela |
| `--workgroup` | sim | texto |  |  |  |
| `--output-location` | sim | texto |  |  |  |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect lakeformation`

Coleta grant, registro de localizacao S3 e data lake settings de UMA tabela.

```bash
sparkforge collect lakeformation --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--database` | sim | texto |  |  | Banco da tabela no catalogo. |
| `--table` | sim | texto |  |  | Nome da tabela. |
| `--catalog-id` | não | texto |  | `` | Id da conta dona do catalogo. Obrigatorio em cross-account: a MESMA `db.tabela` existe em contas diferentes, e sem ele as duas coletas se sobrescrevem no manifesto. |
| `--resource-arn` | não | texto |  | `` | Localizacao S3 a conferir em `describe_resource`. Sem ela o bloco sai `nao_coletado` em vez de sumir -- bloco ausente e indistinguivel de vazio. |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect parquet-footer`

Le so o FOOTER dos Parquet de um prefixo (diretorio local ou s3://): row group, estatistica por coluna e sort order. Nenhuma linha de dado. Exige pyarrow.

```bash
sparkforge collect parquet-footer --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--prefix` | sim | texto |  |  | Diretorio local com .parquet, ou s3://bucket/prefixo/. |
| `--max-files` | não | texto |  |  | Quantos arquivos ler, os primeiros pelo nome (padrao do coletor: 20; teto 500). |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)

## `sparkforge collect verify`

Verifica presenca e integridade de todos os artefatos do manifesto.

```bash
sparkforge collect verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_collect_athena_workgroup`](../tools/sparkforge_collect_athena_workgroup.md), [`sparkforge_collect_cloudwatch`](../tools/sparkforge_collect_cloudwatch.md), [`sparkforge_collect_cloudwatch_logs`](../tools/sparkforge_collect_cloudwatch_logs.md), [`sparkforge_collect_emr_cluster`](../tools/sparkforge_collect_emr_cluster.md), [`sparkforge_collect_emr_eks`](../tools/sparkforge_collect_emr_eks.md), [`sparkforge_collect_emr_serverless`](../tools/sparkforge_collect_emr_serverless.md), [`sparkforge_collect_event_log`](../tools/sparkforge_collect_event_log.md), [`sparkforge_collect_glue_job`](../tools/sparkforge_collect_glue_job.md), [`sparkforge_collect_glue_job_runs`](../tools/sparkforge_collect_glue_job_runs.md), [`sparkforge_collect_glue_resource_link`](../tools/sparkforge_collect_glue_resource_link.md), [`sparkforge_collect_iam_access`](../tools/sparkforge_collect_iam_access.md), [`sparkforge_collect_iceberg_metadata`](../tools/sparkforge_collect_iceberg_metadata.md), [`sparkforge_collect_lakeformation`](../tools/sparkforge_collect_lakeformation.md), [`sparkforge_collect_parquet_footer`](../tools/sparkforge_collect_parquet_footer.md), [`sparkforge_collect_verify`](../tools/sparkforge_collect_verify.md)
